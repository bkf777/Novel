/**
 * 迷你 JSON Schema 校验引擎（draft-07 子集）
 * 依赖：无。Node 内置。
 * 支持：type / required / properties / additionalProperties(false) / items /
 *       enum / const / minimum / maximum / minLength / maxLength / minItems /
 *       maxItems / pattern / $ref(#/definitions/xxx) / oneOf / anyOf
 */

const TYPE_CHECKS = {
  string: (v) => typeof v === 'string',
  number: (v) => typeof v === 'number' && Number.isFinite(v),
  integer: (v) => Number.isInteger(v),
  boolean: (v) => typeof v === 'boolean',
  array: (v) => Array.isArray(v),
  object: (v) => v !== null && typeof v === 'object' && !Array.isArray(v),
  null: (v) => v === null,
};

function typeOf(v) {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  if (Number.isInteger(v)) return 'integer';
  return typeof v;
}

function resolveRef(ref, root) {
  if (!ref.startsWith('#/')) return null;
  const parts = ref.slice(2).split('/').map((p) => p.replace(/~1/g, '/').replace(/~0/g, '~'));
  let node = root;
  for (const p of parts) {
    if (node == null || typeof node !== 'object') return null;
    node = node[p];
  }
  return node;
}

/**
 * @returns {{ok:boolean, errors:string[]}}
 */
export function validate(value, schema, root, path = '$') {
  const errors = [];
  walk(value, schema, root, path, errors);
  return { ok: errors.length === 0, errors };
}

function walk(v, schema, root, path, errors) {
  if (schema === true || schema === undefined) return;
  if (schema === false) {
    errors.push(`${path}: 不允许任何值`);
    return;
  }
  if (schema.$ref) {
    const target = resolveRef(schema.$ref, root);
    if (!target) {
      errors.push(`${path}: 无法解析 $ref ${schema.$ref}`);
      return;
    }
    walk(v, target, root, path, errors);
    return;
  }
  if (schema.oneOf || schema.anyOf) {
    const branches = schema.oneOf || schema.anyOf;
    const matched = branches.some((b) => validate(v, b, root, path).ok);
    if (!matched) {
      errors.push(`${path}: 不满足 oneOf/anyOf 的任何分支`);
      return;
    }
  }

  // type
  if (schema.type !== undefined) {
    const types = Array.isArray(schema.type) ? schema.type : [schema.type];
    const ok = types.some((t) => {
      if (t === 'number') return TYPE_CHECKS.number(v);
      if (t === 'integer') return TYPE_CHECKS.integer(v);
      return TYPE_CHECKS[t] ? TYPE_CHECKS[t](v) : false;
    });
    if (!ok) {
      errors.push(`${path}: 类型应为 ${types.join('|')}，实际 ${typeOf(v)}`);
      return; // 类型错就不继续深查
    }
  }

  // const / enum
  if ('const' in schema && JSON.stringify(v) !== JSON.stringify(schema.const)) {
    errors.push(`${path}: 必须等于 ${JSON.stringify(schema.const)}，实际 ${JSON.stringify(v)}`);
  }
  if (Array.isArray(schema.enum)) {
    const ok = schema.enum.some((e) => JSON.stringify(e) === JSON.stringify(v));
    if (!ok) errors.push(`${path}: 须为枚举值之一 [${schema.enum.join(', ')}]，实际 ${JSON.stringify(v)}`);
  }

  // string
  if (typeof v === 'string') {
    if (schema.minLength !== undefined && v.length < schema.minLength) {
      errors.push(`${path}: 字符串长度 ${v.length} < minLength ${schema.minLength}`);
    }
    if (schema.maxLength !== undefined && v.length > schema.maxLength) {
      errors.push(`${path}: 字符串长度 ${v.length} > maxLength ${schema.maxLength}`);
    }
    if (schema.pattern !== undefined) {
      let re;
      try { re = new RegExp(schema.pattern); } catch { re = null; }
      if (re && !re.test(v)) errors.push(`${path}: 不匹配 pattern /${schema.pattern}/ → "${v}"`);
    }
  }

  // number
  if (typeof v === 'number') {
    if (schema.minimum !== undefined && v < schema.minimum) errors.push(`${path}: ${v} < minimum ${schema.minimum}`);
    if (schema.maximum !== undefined && v > schema.maximum) errors.push(`${path}: ${v} > maximum ${schema.maximum}`);
  }

  // array
  if (Array.isArray(v)) {
    if (schema.minItems !== undefined && v.length < schema.minItems) {
      errors.push(`${path}: 数组长度 ${v.length} < minItems ${schema.minItems}`);
    }
    if (schema.maxItems !== undefined && v.length > schema.maxItems) {
      errors.push(`${path}: 数组长度 ${v.length} > maxItems ${schema.maxItems}`);
    }
    if (schema.items) {
      v.forEach((item, i) => walk(item, schema.items, root, `${path}[${i}]`, errors));
    }
  }

  // object
  if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
    for (const req of schema.required || []) {
      if (!Object.prototype.hasOwnProperty.call(v, req)) {
        errors.push(`${path}: 缺少必填字段 "${req}"`);
      }
    }
    const props = schema.properties || {};
    for (const [k, sub] of Object.entries(props)) {
      if (Object.prototype.hasOwnProperty.call(v, k)) {
        walk(v[k], sub, root, `${path}.${k}`, errors);
      }
    }
    if (schema.additionalProperties === false) {
      const extra = Object.keys(v).filter((k) => !Object.prototype.hasOwnProperty.call(props, k));
      if (extra.length) {
        errors.push(`${path}: 出现未定义字段 [${extra.join(', ')}]（additionalProperties=false）`);
      }
    } else if (schema.additionalProperties && typeof schema.additionalProperties === 'object') {
      const props2 = schema.properties || {};
      for (const k of Object.keys(v)) {
        if (!Object.prototype.hasOwnProperty.call(props2, k)) {
          walk(v[k], schema.additionalProperties, root, `${path}.${k}`, errors);
        }
      }
    }
  }
}
