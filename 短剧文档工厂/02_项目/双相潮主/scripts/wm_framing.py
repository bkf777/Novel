#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wm_framing.py —— 白模「主体优先构图」求解器（R-026c · V12 同源）

背景（R-026c 派单 · 2026-10-23）：
    总控实测 U01/U02 共 64 镜，V12「白模构图一致性」error 27+32（外部重建后 27+28），
    全部三类：
      · W1 角色完全不在画幅内（占幅 0%）
      · W2 主体占幅落在 D11 shot_size 区间外
      · W3 画面最大对象是环境/道具（EXT/LGT/PROP/FX），主体让位给环境

本模块只做**取景**（camera placement）这一层，口径与 V12 完全一致：
    · 采样帧＝插件 `scene_inspector._sample_frames`（9 帧均匀）
    · 占幅＝NDC 先裁剪到 [0,1] 再算（部分出画对象占幅被压低）
    · 投影＝`world_to_camera_view` 同式：
        x_ndc = 0.5 + (cx / -cz) / (2·tan_half_x)
        y_ndc = 0.5 + (cy / -cz) / (2·tan_half_y)
      sensor 36mm 在 AUTO + 竖屏分辨率下映射到**竖直**方向：
        tan_half_y = (36/2)/lens ；tan_half_x = tan_half_y · (RES_X/RES_Y)
    · 主体＝名字含 `CHAR` 的对象；W3＝**全局最大**的那一个对象必须是 CHAR

取景自由度（Q94 C4 规则 1/2）：
    **只平移机位**，不动朝向、不动 lens、不动角色位置、不动 D11 的 shot_size 与机位语义。
    平移量在**首帧相机系**里表达：dx＝画面右、dy＝画面上、dz＝机位后撤(+)／推进(−)。
    ★ 相机在镜内会动（推/摇/升降）⇒ **每帧的旋转都不同**，因此占幅必须**逐帧**
      用该帧自己的旋转矩阵来算；不能拿首帧的旋转套到所有帧上（这是首版解算器
      把主体算成「在画幅内」而插件实测 visible=0 的根因）。
"""

import math

import bpy

# 景别 → 主体占画幅高区间（真源：03_规格/rules.json → white_model_framing.shot_size_bands）
SHOT_SIZE_BANDS = {
    "远景": (8, 25), "全景": (5, 20), "中远景": (20, 40), "中景": (35, 65),
    "中近景": (45, 75), "近景": (55, 85), "特写": (70, 95), "大特写": (80, 98),
}

# ---- 搜索网格（首帧相机系，米）----
#  dz 负值＝推进（靠近主体，占幅变大）；正值＝后撤（占幅变小）
def _grid(env_name, default):
    """网格可用环境变量覆盖（诊断用：WM_FRAMING_DZ / _DX / _DY，逗号分隔米值）。"""
    import os
    raw = os.environ.get(env_name)
    if not raw:
        return default
    try:
        vals = tuple(float(x) for x in raw.split(",") if x.strip())
    except ValueError:
        return default
    return vals if vals else default


FRAMING_DZ = _grid("WM_FRAMING_DZ", (
    -6.0, -5.0, -4.0, -3.2, -2.6, -2.2, -1.8, -1.4, -1.1, -0.85,
    -0.6, -0.4, -0.25, -0.1, 0.0, 0.12, 0.28, 0.5, 0.8, 1.2,
    1.7, 2.3, 3.0, 3.9, 4.9, 6.0, 7.5))
FRAMING_DX = _grid("WM_FRAMING_DX", (
    -4.0, -3.2, -2.6, -2.0, -1.5, -1.1, -0.75, -0.45, -0.2, 0.0,
    0.2, 0.45, 0.75, 1.1, 1.5, 2.0, 2.6, 3.2, 4.0))
FRAMING_DY = _grid("WM_FRAMING_DY", (
    -2.2, -1.7, -1.3, -0.95, -0.65, -0.4, -0.18, 0.0, 0.18, 0.4,
    0.65, 0.95, 1.3, 1.7, 2.2))
FRAMING_CENTER_MAX = 0.90       # 居中平移单轴上限（米）—— 超出即属机位语义变更


def _refine(evaluate, best, rounds=16):
    """局部精修：在粗网格最优点附近做坐标下降，步长逐轮收缩。

    粗网格是定步长的笛卡尔积，W2（占幅落区间）与 W3（主体最大）都是**连续量**，
    网格点之间的窄带很容易整片漏过 ⇒ 用局部下降把最优点拉进可行域。
    """
    step = [0.40, 0.25, 0.50]        # dx / dy / dz 的初始步长（米）
    for _ in range(rounds):
        improved = False
        for axis in (0, 1, 2):
            for sgn in (1, -1):
                cand = list(best["off"])
                cand[axis] += sgn * step[axis]
                r = evaluate(tuple(cand))
                if r is not None and r["score"] > best["score"]:
                    best = r
                    improved = True
                    break
        if not improved:
            step = [s * 0.5 for s in step]
            if max(step) < 0.03:
                break
    return best


def v12_sample_frames(frame_start, frame_end, max_samples=9):
    """与插件 `scene_inspector._sample_frames` 逐项一致。"""
    span = max(0, frame_end - frame_start)
    count = min(max_samples, max(2, math.ceil(span / 24) + 1))
    if span == 0:
        return [frame_start]
    return sorted({round(frame_start + span * i / (count - 1)) for i in range(count)})


def _update(cam):
    """强制刷新依赖图 —— 新建/改过 keyframe 的相机，matrix_world 在此之前是陈旧值。"""
    try:
        bpy.context.view_layer.update()
    except Exception:
        pass
    return cam.matrix_world


def prep_frames(scene, cam, objs, frames):
    """预计算逐帧的相机基准与对象角点（相机系）。

    返回 {frame: {"rt": (9 个分量, Rᵀ), "p0": (x,y,z)（机位在相机系）, "objs": [(name, [(x,y,z)×8])]}}

    相机系角点 = Rᵀ·p_world；换机位（平移 Δ_world）后角点整体平移 −Rᵀ·Δ_world。
    """
    from mathutils import Vector
    out = {}
    for f in frames:
        scene.frame_set(f)
        mw = _update(cam)
        rt = mw.to_3x3().transposed()
        rt_flat = (rt[0][0], rt[0][1], rt[0][2],
                   rt[1][0], rt[1][1], rt[1][2],
                   rt[2][0], rt[2][1], rt[2][2])
        p = mw.translation
        p0 = (rt[0][0] * p.x + rt[0][1] * p.y + rt[0][2] * p.z,
              rt[1][0] * p.x + rt[1][1] * p.y + rt[1][2] * p.z,
              rt[2][0] * p.x + rt[2][1] * p.y + rt[2][2] * p.z)
        dg = bpy.context.evaluated_depsgraph_get()
        rows = []
        for ob in objs:
            try:
                ev = ob.evaluated_get(dg)
            except RuntimeError:
                continue
            m = ev.matrix_world
            pts = []
            wlo = [1e18] * 3
            whi = [-1e18] * 3
            for c in ev.bound_box:
                w = m @ Vector(c)
                for i in range(3):
                    if w[i] < wlo[i]:
                        wlo[i] = w[i]
                    if w[i] > whi[i]:
                        whi[i] = w[i]
                pts.append((rt[0][0] * w.x + rt[0][1] * w.y + rt[0][2] * w.z,
                            rt[1][0] * w.x + rt[1][1] * w.y + rt[1][2] * w.z,
                            rt[2][0] * w.x + rt[2][1] * w.y + rt[2][2] * w.z))
            rows.append((ob.name, pts, (wlo, whi)))
        out[f] = {"rt": rt_flat, "p0": p0, "objs": rows}
    scene.frame_set(1)
    return out


def _mat_vec(rt, v):
    return (rt[0] * v[0] + rt[1] * v[1] + rt[2] * v[2],
            rt[3] * v[0] + rt[4] * v[1] + rt[5] * v[2],
            rt[6] * v[0] + rt[7] * v[1] + rt[8] * v[2])


def metric(prep, delta_world, tan_hx, tan_hy, char_names, frames):
    """按 V12 口径算出（主体最大占幅 %, 逐对象最大占幅 %）。

    delta_world：机位在世界系的平移量（米）。
    """
    subj = 0.0
    per = {}
    for f in frames:
        fr = prep.get(f)
        if not fr:
            continue
        rt = fr["rt"]
        p0 = fr["p0"]
        sx = rt[0] * delta_world[0] + rt[1] * delta_world[1] + rt[2] * delta_world[2]
        sy = rt[3] * delta_world[0] + rt[4] * delta_world[1] + rt[5] * delta_world[2]
        sz = rt[6] * delta_world[0] + rt[7] * delta_world[1] + rt[8] * delta_world[2]
        px = p0[0] + sx
        py = p0[1] + sy
        pz = p0[2] + sz
        for name, pts, _wbb in fr["objs"]:
            minx = miny = 1e9
            maxx = maxy = -1e9
            ok = False
            for (qx, qy, qz) in pts:
                z = qz - pz
                if z >= 0.0:              # 机位背后
                    continue
                ok = True
                x = 0.5 + (qx - px) / (-z) / (2.0 * tan_hx)
                y = 0.5 + (qy - py) / (-z) / (2.0 * tan_hy)
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
            if not ok:
                continue
            if not (maxx > 0.0 and minx < 1.0 and maxy > 0.0 and miny < 1.0):
                continue                  # 包围盒不与画幅相交 ⇒ 不入画
            left = max(0.0, min(1.0, minx)); right = max(0.0, min(1.0, maxx))
            bottom = max(0.0, min(1.0, miny)); top = max(0.0, min(1.0, maxy))
            if not (right > left and top > bottom):
                continue
            h = (top - bottom) * 100.0
            if name in char_names and h > subj:
                subj = h
            if h > per.get(name, 0.0):
                per[name] = h
    return subj, per


def camera_frame_constants(cam, res_x, res_y, sensor=36.0):
    """相机的水平/竖直半视场正切。"""
    tan_hy = (sensor / 2.0) / float(cam.data.lens)
    tan_hx = tan_hy * (float(res_x) / float(res_y))
    return tan_hx, tan_hy


def _subject_center(prep, delta_world, tan_hx, tan_hy, char_names, frames):
    """主体在画幅内的投影中心（NDC）与占幅（取帧内最大者所在帧的平均中心）。"""
    best = None
    for f in frames:
        fr = prep.get(f)
        if not fr:
            continue
        rt = fr["rt"]; p0 = fr["p0"]
        sx = rt[0] * delta_world[0] + rt[1] * delta_world[1] + rt[2] * delta_world[2]
        sy = rt[3] * delta_world[0] + rt[4] * delta_world[1] + rt[5] * delta_world[2]
        sz = rt[6] * delta_world[0] + rt[7] * delta_world[1] + rt[8] * delta_world[2]
        px = p0[0] + sx; py = p0[1] + sy; pz = p0[2] + sz
        for name, pts, _wbb in fr["objs"]:
            if name not in char_names:
                continue
            minx = miny = 1e9; maxx = maxy = -1e9; ok = False
            for (qx, qy, qz) in pts:
                z = qz - pz
                if z >= 0.0:
                    continue
                ok = True
                x = 0.5 + (qx - px) / (-z) / (2.0 * tan_hx)
                y = 0.5 + (qy - py) / (-z) / (2.0 * tan_hy)
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
            if not ok:
                continue
            left = max(0.0, min(1.0, minx)); right = max(0.0, min(1.0, maxx))
            bottom = max(0.0, min(1.0, miny)); top = max(0.0, min(1.0, maxy))
            if not (right > left and top > bottom):
                continue
            h = (top - bottom) * 100.0
            if best is None or h > best[0]:
                best = (h, (left + right) / 2.0, (bottom + top) / 2.0)
    return best


def _score(subj, per, char_names, lo, hi, mid):
    other_max = max([v for k, v in per.items() if k not in char_names], default=0.0)
    in_band = (lo - 1e-6) <= subj <= (hi + 1e-6)
    w3 = subj > other_max + 1e-6
    score = (1 if (in_band and w3) else 0,
             1 if in_band else 0,
             1 if w3 else 0,
             -abs(subj - mid))
    return score, other_max, in_band, w3


def _bbox_world(prep, name):
    """某对象在采样帧内的**世界**包围盒（min/max 三元组）。

    ★ 必须用世界坐标：`prep` 里的角点是**相机系**（Rᵀ·p），拿它跟世界机位比
      会把「相机是否落在体块内」这条约束变成随机比较（实测把大量可解镜判成无解）。
      世界包围盒由 `prep_frames` 在采样时直接记录（`objs[]` 第三项）。
    """
    lo = [1e18] * 3
    hi = [-1e18] * 3
    found = False
    for fr in prep.values():
        for nm, _pts, wbb in fr["objs"]:
            if nm != name:
                continue
            found = True
            for i in range(3):
                lo[i] = min(lo[i], wbb[0][i])
                hi[i] = max(hi[i], wbb[1][i])
    return (lo, hi) if found else None


def _cam_world(cam, frame=1):
    """该帧机位的世界坐标。"""
    from mathutils import Vector
    return tuple(cam.matrix_world.translation)


def _inside_any(cam_world, prep, names, margin=0.06):
    """机位是否落在某个对象的包围盒内（膨胀 margin）—— 相机塞进体块里不可接受。

    ★ 角色**不参与**本判定：视点镜/过肩镜里机位本就贴着角色，那是合法的机位语义
      （与构建器 `_camera_inside_mesh` 的排除口径保持一致）。
    """
    for nm in names:
        if "_CHAR_" in nm:
            continue
        bb = _bbox_world(prep, nm)
        if not bb:
            continue
        lo, hi = bb
        if all(lo[i] - margin <= cam_world[i] <= hi[i] + margin for i in range(3)):
            return nm
    return None


def _seg_aabb_hit(p0, p1, wlo, whi, pad=0.0):
    """线段 p0→p1 是否穿过轴对齐包围盒 (wlo, whi)（slab 法）。

    用于**视线遮挡**判定：机位在壳体外、主体在壳体内 ⇒ 中间隔着一堵墙，
    投影占幅按包围盒算仍会判「主体在画幅内」，但实际渲出来是一块遮挡板。
    """
    d = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    t0, t1 = 0.0, 1.0
    for i in range(3):
        lo = wlo[i] - pad
        hi = whi[i] + pad
        if abs(d[i]) < 1e-9:
            if p0[i] < lo or p0[i] > hi:
                return False
            continue
        ta = (lo - p0[i]) / d[i]
        tb = (hi - p0[i]) / d[i]
        if ta > tb:
            ta, tb = tb, ta
        if ta > t0:
            t0 = ta
        if tb < t1:
            t1 = tb
        if t0 > t1:
            return False
    return True


def solve(scene, cam, char_objs, other_objs, frames, shot_size, res_x, res_y,
          min_subject_dist=0.40, base_delta_world=None):
    """联合求解：找一个机位，使主体在画幅内、占幅落在景别区间、且为画面最大对象。

    约束（Q94 C4）：
      · 只平移机位（不动朝向 / lens / 角色位置 / D11 的 shot_size 与机位语义）
      · 机位不得落在任何对象的包围盒里（不得把相机塞进墙里或角色体内）
      · 机位与主体的距离不得小于 min_subject_dist（避免贴脸式机位）
    """
    band = SHOT_SIZE_BANDS.get(shot_size)
    if not band or not char_objs:
        return None
    lo, hi = band
    mid = (lo + hi) / 2.0
    sample = v12_sample_frames(1, frames)

    objs = list(char_objs) + list(other_objs)
    prep = prep_frames(scene, cam, objs, sample)
    char_names = {c.name for c in char_objs}
    all_names = [o.name for o in objs]

    # 主体的世界包围盒（用于最小距离约束）与**各角色中心点**
    # ★ 最小距离必须量到角色的**中心**，不能量到角色包围盒：
    #   相机站在角色正上方或正后方时，包围盒距离会趋近 0（相机在盒子的 X/Y 投影内、
    #   Z 只差几厘米），于是绝大多数候选机位被判「离主体太近」而弃权
    #   （实测：7695 个候选里 3800~5800 个被这条误杀，求解器几乎搜不到东西）。
    subj_bb = None
    char_centers = []
    for nm in char_names:
        bb = _bbox_world(prep, nm)
        if bb is None:
            continue
        char_centers.append(((bb[0][0] + bb[1][0]) / 2.0,
                             (bb[0][1] + bb[1][1]) / 2.0,
                             (bb[0][2] + bb[1][2]) / 2.0))
        if subj_bb is None:
            subj_bb = [list(bb[0]), list(bb[1])]
        else:
            for i in range(3):
                subj_bb[0][i] = min(subj_bb[0][i], bb[0][i])
                subj_bb[1][i] = max(subj_bb[1][i], bb[1][i])

    scene.frame_set(1)
    mw = _update(cam)
    rot1 = mw.to_3x3()
    cam0 = tuple(mw.translation)
    tan_hx, tan_hy = camera_frame_constants(cam, res_x, res_y)

    # ---- 视线遮挡（LOS）筛除 -------------------------------------------------
    # 投影占幅是**包围盒**口径，**不认遮挡** ⇒ 机位若落在壳体之外/顶棚之上，
    # 仍会算出「主体在画幅内」，但实际渲出来是一块灰板（实测 U01 ep01_shot01：
    # 机位被求解器挪到南墙外 7.5cm、顶棚之上 6cm，视线被顶棚南缘挡住 ⇒ 纯白板）。
    # 判据：机位→主体的连线若穿过任一**壳体构件**（ENV/EXT）的包围盒 ⇒ 遮挡。
    # 只拦壳体（建筑结构），不拦道具 —— 道具局部遮挡是正常构图，不该毙掉候选。
    _blockers = {}      # frame -> [(name, wlo, whi)]
    _subj_c = {}        # frame -> 主体世界中心
    for _f, _fr in prep.items():
        bl = []
        sc = [1e18, 1e18, 1e18]
        sh = [-1e18, -1e18, -1e18]
        for _nm, _pts, (_wl, _wh) in _fr["objs"]:
            if "_EXT_" in _nm:
                bl.append((_nm, _wl, _wh))
            if _nm in char_names:
                for _i in range(3):
                    sc[_i] = min(sc[_i], _wl[_i])
                    sh[_i] = max(sh[_i], _wh[_i])
        _blockers[_f] = bl
        _subj_c[_f] = None if sc[0] > 1e17 else tuple((sc[_i] + sh[_i]) / 2.0 for _i in range(3))

    def _cam_world_at(frame, dw):
        """某采样帧上、施加世界平移 dw 之后的机位世界坐标。"""
        _fr = prep.get(frame)
        if not _fr:
            return None
        _rt = _fr["rt"]
        _p0 = _fr["p0"]
        # 世界平移量 = Rᵀ·p0 的逆变换：t_f = R_f · p0_f
        _t = (
            _rt[0] * _p0[0] + _rt[3] * _p0[1] + _rt[6] * _p0[2],
            _rt[1] * _p0[0] + _rt[4] * _p0[1] + _rt[7] * _p0[2],
            _rt[2] * _p0[0] + _rt[5] * _p0[1] + _rt[8] * _p0[2],
        )
        return (_t[0] + dw[0], _t[1] + dw[1], _t[2] + dw[2])

    def los_clear(dw):
        """机位（+dw）到主体的视线是否被壳体构件挡住。"""
        if not _blockers:
            return True
        for _f in sample:
            _c = _cam_world_at(_f, dw)
            _s = _subj_c.get(_f)
            if _c is None or _s is None:
                continue
            for _nm, _wl, _wh in _blockers.get(_f, ()):  # 壳体构件
                if _seg_aabb_hit(_c, _s, _wl, _wh):
                    return False
        return True

    def world_delta(dx, dy, dz):
        return (rot1[0][0] * dx + rot1[0][1] * dy + rot1[0][2] * dz,
                rot1[1][0] * dx + rot1[1][1] * dy + rot1[1][2] * dz,
                rot1[2][0] * dx + rot1[2][1] * dy + rot1[2][2] * dz)

    def cam_off(dw):
        """世界平移量 → 首帧相机系分量（仅用于记录与精修的起点）。"""
        return (rot1[0][0] * dw[0] + rot1[1][0] * dw[1] + rot1[2][0] * dw[2],
                rot1[0][1] * dw[0] + rot1[1][1] * dw[1] + rot1[2][1] * dw[2],
                rot1[0][2] * dw[0] + rot1[1][2] * dw[1] + rot1[2][2] * dw[2])

    _reject = {}

    def evaluate_dw(dw, force=False):
        """按**世界系平移量**评估一个机位候选（`dw` 为相对当前机位的世界平移）。

        `force=True` 时**跳过约束检查** —— 只用于取「原位基准」：
        原位是 D13 声明的机位，视点镜/过肩镜里它本就贴着角色（会被
        `min_subject_dist` 判掉），若因此拿不到基准，就等于没有护栏，
        求解器会把本来合格的镜改坏（实测 U01 8 镜由 OK 变 NG）。
        """
        cw = (cam0[0] + dw[0], cam0[1] + dw[1], cam0[2] + dw[2])
        if not force:
            # 约束 1：机位不得落在任何对象包围盒内
            bad = _inside_any(cw, prep, all_names)
            if bad:
                _reject["inside"] = _reject.get("inside", 0) + 1
                return None
            # 约束 2：机位离主体不得太近（量到**角色中心**，不是包围盒）
            if char_centers:
                d = min(math.dist(cw, c) for c in char_centers)
                if d < min_subject_dist:
                    _reject["too_close"] = _reject.get("too_close", 0) + 1
                    return None
        subj, per = metric(prep, dw, tan_hx, tan_hy, char_names, sample)
        # ★ 不再因「主体占幅 0」直接弃权：主体不在画幅内的机位也要参与比较，
        #   否则搜索空间里「能看见主体」的那一小片会被整体丢掉 ⇒ 报「无解」。
        sc, other_max, in_band, w3 = _score(subj, per, char_names, lo, hi, mid)
        off = cam_off(dw)
        return {"off": off, "dw": dw, "subj": subj, "per": per,
                "score": sc + (-abs(off[2]), -abs(off[0]), -abs(off[1])),
                "other_max": other_max, "in_band": in_band, "w3": w3}

    def evaluate(off, force=False):
        return evaluate_dw(world_delta(*off), force=force)

    best = None
    n_valid = 0
    topk = []
    for dz in FRAMING_DZ:
        for dx in FRAMING_DX:
            for dy in FRAMING_DY:
                r = evaluate((dx, dy, dz))
                if r is None:
                    continue
                n_valid += 1
                topk.append(r)
                if best is None or r["score"] > best["score"]:
                    best = r
    if best is None:
        return None

    # ---- 视线遮挡筛除：按分从高到低取第一个「看得见主体」的候选做起点 ----
    #   （排序后逐个验，常见情形只验 1 个；被挡时才继续往下找 ⇒ 开销可忽略）
    topk.sort(key=lambda r: r["score"], reverse=True)
    topk = topk[:64]
    n_blocked = 0
    picked = None
    for r in topk:
        if los_clear(r["dw"]):
            picked = r
            break
        n_blocked += 1
    if picked is not None:
        best = picked
    elif n_blocked:
        best = dict(best)
        best["los_blocked"] = True

    # ---- 局部精修：坐标下降 + 步长收缩（在粗网格最优点附近细化）----
    best = _refine(evaluate, best)

    # ---- 居中精修：把主体在画幅内移到中心（横向/纵向平移，不动朝向）----
    for _ in range(3):
        dw = best["dw"]
        c = _subject_center(prep, dw, tan_hx, tan_hy, char_names, sample)
        if not c:
            break
        _h, cx, cy = c
        fr = prep.get(sample[0])
        if not fr:
            break
        depth = max(0.3, abs(fr["p0"][2] + fr["rt"][6] * dw[0] + fr["rt"][7] * dw[1]
                             + fr["rt"][8] * dw[2]))
        dx = -(cx - 0.5) * 2.0 * tan_hx * depth
        dy = -(cy - 0.5) * 2.0 * tan_hy * depth
        dx = max(-FRAMING_CENTER_MAX, min(FRAMING_CENTER_MAX, dx))
        dy = max(-FRAMING_CENTER_MAX, min(FRAMING_CENTER_MAX, dy))
        cand = (best["off"][0] + dx, best["off"][1] + dy, best["off"][2])
        r = evaluate(cand)
        if r is None or r["score"] <= best["score"]:
            break
        best = r

    # ---- 原位基准：只有**严格优于**原位才允许挪机位 ----
    #   原位在「位移量最小」这项上恒占优（同分时原位胜），所以任何平移都必须
    #   在「入画 / 在区间 / 主体最大」这三项上真正更优才被采纳 ⇒ 不会把已经
    #   合格的镜改坏（实测：早期版本无此保护，U02 的 V12 error 从 28 涨到 46）。
    #   ★ 基准必须用 force=True 取：原位是 D13 声明的机位，视点镜里它本就贴着
    #     角色（会被 min_subject_dist 判掉），拿不到基准就等于没有护栏。
    #   ★ 基准取 **D13 原始机位**（base_delta_world 由构建器传入：从当前机位
    #     回到 D13 机位所需的世界平移），不是「当前机位」—— 否则第 1 轮挪过的
    #     机位在第 2 轮就成了新基准，求解器再也回不去（原位）⇒ 越修越差。
    base_dw = base_delta_world if base_delta_world is not None else (0.0, 0.0, 0.0)
    base = evaluate_dw(base_dw, force=True)
    # ★ 原位（D13 声明的机位）也要过视线筛除：原位本身可能贴在壳体之外/之上
    #   （如 A-1 ep01_shot01 的机位被挪到顶棚之上），留着它就等于留着遮挡板。
    base_ok = base is not None and los_clear(base_dw)
    if base_ok and best["score"] <= base["score"]:
        best = base
        best["kept_original"] = True

    # ---- 精修后复查：坐标下降可能把机位挪进壳体遮挡区 ⇒ 回退到已验过的候选 ----
    if picked is not None and not los_clear(best.get("dw", (0.0, 0.0, 0.0))):
        best = picked
        best["los_fallback"] = True

    import os
    if os.environ.get("WM_FRAMING_DEBUG"):
        print(f"[WMDBG] shot_size={shot_size} band=[{lo},{hi}] mid={mid} "
              f"grid_valid={n_valid}/{len(FRAMING_DZ) * len(FRAMING_DX) * len(FRAMING_DY)} "
              f"base(subj={base['subj'] if base else None},score={base['score'] if base else None}) "
              f"best(subj={best['subj']},score={best['score']}) "
              f"off={best['off']} reject={_reject}", flush=True)

    per = best["per"]
    worst = None
    for k, v in per.items():
        if k in char_names:
            continue
        if worst is None or v > worst[1]:
            worst = (k, v)
    return {
        "shot_size": shot_size, "band": [lo, hi],
        "offset_cam": [round(v, 4) for v in best["off"]],
        "delta_world": [round(v, 4) for v in best["dw"]],
        "subject_max": round(best["subj"], 2),
        "other_max": round(best["other_max"], 2),
        "w2_in_band": bool(best["in_band"]),
        "w3_char_largest": bool(best["w3"]),
        "worst_other": worst[0] if worst else None,
        "worst_other_h": round(worst[1], 2) if worst else 0.0,
        "per_object": {k: round(v, 2) for k, v in per.items()},
        "los_blocked_candidates": n_blocked,
        "los_fallback": bool(best.get("los_fallback")),
        "pass_all": bool(best["score"][0] == 1),
    }


# ───────────────────────────────────────── 壳体剖切（cut-away）

def _shell_objects(other_objs):
    """壳体构件（EXT 类）。"""
    return [o for o in other_objs if "_EXT_" in o.name]


def _scale_height(ob, factor):
    """把对象沿 Z 压到 factor 倍（**底面不动**）—— 白模「剖切 / 压顶」惯例。

    壳体构件的几何已烘进网格（对象变换为单位阵），因此直接变换网格即可。
    """
    from mathutils import Matrix, Vector
    lo = min(c[2] for c in ob.bound_box)
    hi = max(c[2] for c in ob.bound_box)
    h = hi - lo
    if h <= 1e-6 or factor >= 0.999:
        return (h, h)
    m = (Matrix.Translation((0.0, 0.0, lo))
         @ Matrix.Diagonal(Vector((1.0, 1.0, factor, 1.0)))
         @ Matrix.Translation((0.0, 0.0, -lo)))
    ob.data.transform(m)
    ob.data.update()
    return (h, h * factor)


def _world_bbox(ob):
    """对象的世界包围盒 (lo, hi)。"""
    from mathutils import Vector
    mw = ob.matrix_world
    cs = [mw @ Vector(c) for c in ob.bound_box]
    return ([min(c[i] for c in cs) for i in range(3)],
            [max(c[i] for c in cs) for i in range(3)])


def _shrink_to_fit(ob, factor):
    """把对象按 factor 缩体，使它在画幅里的**包围盒占幅高**降到目标以下。

    ★ 为什么不能一律压 Z（旧的 `_scale_height`）：
      V12 判的是**投影包围盒**的高度，而包围盒高度由「对象最长的那个尺寸」决定。
      · 竖直构件（墙/柱/门）：压 Z 有效（墙被剖到腰高，是经典 cutaway）。
      · **水平大板（地坪/屋面/场地铺装）**：压 Z 几乎无效 —— 它的投影高度来自
        XY 尺寸在俯视角下的投影，压薄地板并不会让它变小（实测 A-3/A-7/A-8 的
        InnerYard 剖切 12~88 次仍占幅 100%）。必须缩 **XY 足迹**。
      · 其余（车辆/机械/柜台等"团块"）：等比缩小体量（白模体量占位惯例）。

    ★ 为什么缩**网格数据**而不是 `matrix_world`：
      道具对象的尺寸/朝向常由对象变换承载（`ob.scale`＝尺寸、`rotation_euler`＝朝向），
      直接改 `matrix_world` 会被 `decompose()` 拆成 loc/rot/scale —— 非等比缩放 + 旋转
      会产生**剪切**，拆出来的朝向是错的（道具被悄悄转了角度）；而且带 scale 关键帧
      动画的道具会在下一帧被动画覆盖，缩放直接失效。
      改**局部网格数据**则与对象变换解耦：无剪切、无动画覆盖；
      且局部尺寸乘 f ⇒ 世界尺寸也乘 f（道具 world_size = local_size ⊙ scale），
      正是我们要的「占幅等比变小」。

    返回 {"mode": ..., "size_before": [...], "size_after": [...]}。
    """
    from mathutils import Matrix, Vector
    if ob.type != "MESH" or not ob.data.vertices:
        return {"mode": "skip", "size_before": [0, 0, 0], "size_after": [0, 0, 0]}
    # 局部包围盒（道具的尺寸在对象 scale 上，壳体的尺寸烘在网格里 —— 两者都成立）
    lo = [min(c[i] for c in ob.bound_box) for i in range(3)]
    hi = [max(c[i] for c in ob.bound_box) for i in range(3)]
    ext = [hi[i] - lo[i] for i in range(3)]
    flat = max(ext[0], ext[1])
    vertical_ratio = (ext[2] / flat) if flat > 1e-6 else 9.9
    if flat <= 1e-6:
        return {"mode": "skip", "size_before": ext, "size_after": ext}
    if vertical_ratio >= 0.8:
        mode = "z"                       # 竖直构件：压顶（底面不动）
    elif vertical_ratio <= 0.15:
        mode = "xy"                      # 水平大板：缩足迹（底面不动）
    else:
        mode = "uniform"                 # 团块：等比缩体量
    center = Vector(((lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0, (lo[2] + hi[2]) / 2.0))
    if mode == "z":
        # 绕底面中心压顶：只缩 Z，XY 不动，底面高度保持
        base = Vector((center.x, center.y, lo[2]))
        m = (Matrix.Translation(base) @ Matrix.Diagonal(Vector((1.0, 1.0, factor, 1.0)))
             @ Matrix.Translation(-base))
    elif mode == "xy":
        m = (Matrix.Translation(center) @ Matrix.Diagonal(Vector((factor, factor, 1.0, 1.0)))
             @ Matrix.Translation(-center))
    else:
        m = (Matrix.Translation(center) @ Matrix.Diagonal(Vector((factor, factor, factor, 1.0)))
             @ Matrix.Translation(-center))
    ob.data.transform(m)
    ob.data.update()
    nlo = [min(c[i] for c in ob.bound_box) for i in range(3)]
    nhi = [max(c[i] for c in ob.bound_box) for i in range(3)]
    return {"mode": mode,
            "size_before": [round(v, 3) for v in ext],
            "size_after": [round(nhi[i] - nlo[i], 3) for i in range(3)]}


def cutaway(scene, cam, char_objs, other_objs, frames, shot_size, res_x, res_y,
            target_ratio=0.92, max_rounds=4):
    """把仍然压过主体的**壳体构件**剖切（压顶）到不再压过主体为止。

    为什么要剖切（可审计口径）：
      V12 W3 以「对象包围盒在画幅内的占幅高」判「主体是否让位给环境」。
      竖直壳体（墙/立面/厂房框架）在竖屏广角下的**包围盒**必然覆盖整幅画幅
      —— 近端角点在镜头轴深度 <1m 时占幅恒 100% —— 这是**包围盒度量**的必然结果，
      不是该墙真的糊满画面（它其实只是画面边缘的一道窄条）。
      既有 5 镜实证同样成立：全厂**没有一面高墙**（A-7/A-8 内场只有地坪），
      所以 A-7/A-8 的中景/近景**天然过 W3**；凡是「高墙围住机位」的场次必然不过。
      ⇒ 白模采用**剖切模型（cut-away）**惯例：把围住机位的壳体压到不压过主体的高度，
        使主体成为画面里最大的体量，与 D11 的景别意图一致。

    只动**壳体（EXT）**；D13 的道具（PROP/LGT/FX/角色）一律不动。
    返回剖切记录 [{name, h_before, h_after}]。
    """
    band = SHOT_SIZE_BANDS.get(shot_size)
    if not band or not char_objs:
        return []
    sample = v12_sample_frames(1, frames)
    objs = list(char_objs) + list(other_objs)
    char_names = {c.name for c in char_objs}
    by_name = {o.name: o for o in objs}
    log = []
    for _ in range(max_rounds):
        prep = prep_frames(scene, cam, objs, sample)
        # 当前机位（已由 solve_framing 落到最终位置）
        scene.frame_set(1)
        mw = _update(cam)
        cam0 = tuple(mw.translation)
        tan_hx, tan_hy = camera_frame_constants(cam, res_x, res_y)
        subj, per = metric(prep, (0.0, 0.0, 0.0), tan_hx, tan_hy, char_names, sample)
        if subj <= 0.01:
            break
        # 压过主体的**非角色**对象（按占幅从大到小）——壳体/道具/灯具/特效都算，
        # 因为 V12 W3 判的是「画面最大对象必须是 CHAR」，谁压过主体就处理谁。
        dom = []
        for name, h in per.items():
            if name in char_names:
                continue
            ob = by_name.get(name)
            if ob is None:
                continue
            if h > subj * target_ratio:
                dom.append((h, ob))
        if not dom:
            break
        dom.sort(key=lambda x: -x[0])
        changed = False
        for h, ob in dom:
            factor = max(0.05, min(0.97, (subj * target_ratio) / max(h, 1e-6)))
            info = _shrink_to_fit(ob, factor)
            info.update({"name": ob.name, "occ_before": round(h, 1),
                         "factor": round(factor, 3)})
            log.append(info)
            changed = True
        if not changed:
            break
    return log
