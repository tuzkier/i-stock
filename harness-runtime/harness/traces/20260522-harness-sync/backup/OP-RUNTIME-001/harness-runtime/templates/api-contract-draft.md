# API Contract Draft — {{mission_id}}

> **触发条件**：本 mission 涉及前端 UI 且 `harness config snapshot` 返回 `prototype.delivery_mode=frontend_engineering`。
> **作用**：interaction stage（prototype-as-frontend 路线）的输入。frontend-prototype-engineer 据此把 `lib/types/` 抽出来作为 shared types draft，并据此写 MSW handler；后续 tech-design 冻结后由 execute 阶段联调真后端。
> **方法论**：`docs/methodologies/prototype-as-frontend-delivery.md` §5.3、§6.6。
> **粒度**：草案。不需要枚举每个字段；列出 endpoint、关键 request/response 形状、状态枚举、错误码即可。后续在 interaction stage frozen 到 `lib/types/`。

---

## 1. Endpoints 总览

| Method | Path | 描述 | traces_to AC | 备注（鉴权 / 幂等 / 限流） |
|---|---|---|---|---|
| GET | `/api/<resource>` | <一句话描述> | AC-01 | <auth/idempotent/rate-limit> |
| POST | `/api/<resource>` | <一句话描述> | AC-02 | |

---

## 2. Shared Types 草图

> 用 TypeScript 语法描述领域实体、状态枚举、Request / Response 形状。frontend-prototype-engineer 据此落到 `{frontend_project_root}/lib/types/` draft。

```ts
// 领域实体
export interface <Entity> {
  id: string;
  // ...
}

// 状态枚举
export type <Entity>State =
  | "<state-1>"
  | "<state-2>";

// 能力快照 / value object（按需）
export interface <ValueObject> {
  // ...
}

// API 响应
export interface <Entity>Response {
  // ...
}

// API 请求
export interface Create<Entity>Request {
  // ...
}
```

---

## 3. 错误码 & 错误响应形状

| Code | HTTP Status | 含义 | 用户文案（默认中文） |
|---|---|---|---|
| `<error-code>` | 422 | <含义> | <用户可见提示> |

```ts
export interface ApiError {
  code: string;     // 上表 Code 列
  message: string;  // 用户可见文案
  details?: Record<string, unknown>;
}
```

---

## 4. 演示分支 scenarios

> 用于 MSW `mocks/scenarios/`；UI 在 dev / preview env 暴露切换器。

| Scenario ID | 名称 | 覆盖 endpoint | 行为差异 | traces_to AC |
|---|---|---|---|---|
| `happy` | 正常路径 | (all) | 默认 fixture | AC-01 |
| `<auth-failed>` | 鉴权失败 | `POST /api/<resource>/start` | 返回 401 + auth_failed | AC-X |
| `<empty-state>` | 空数据 | `GET /api/<resource>` | 返回 `[]` | AC-Y |

---

## 5. 鉴权 / 权限 / 数据边界

- 鉴权方式：<bearer / session / oauth>
- 权限模型：<role-based / capability-based / per-resource>
- 数据边界：<workspace / tenant / user / public>

---

## 6. 非 endpoint 形态（如有）

- Webhook / SSE / WebSocket / 文件上传：<endpoint + 协议 + payload 形状>

---

## 7. 已知 open questions

> 影响契约形状但当前未定的点。interaction stage frozen `lib/types/` 之前必须解决，否则发起 Decision Gate 或路由回 prd。

- [ ] <question>
