# 后端 Schema 拆分设计

## Boundaries And Ownership

- `server/schemas.py` 唯一拥有 FastAPI 请求与领域载荷的 Pydantic 类定义。
- `server/app.py` 继续拥有 FastAPI app、路由、后台任务和当前业务实现，通过显式导入消费并重导出 schema 名称。
- `tests/app/test_schemas.py` 拥有旧导入路径的兼容回归；各功能模块的 API 测试继续验证字段校验和响应行为。

## Dependency Direction

```text
typing + pydantic
        |
        v
 server/schemas.py
        |
        v
   server/app.py -> FastAPI routes / services / runtime state
```

`server/schemas.py` 不可反向导入 `server.app`、FastAPI、DashScope、FFmpeg、路径常量或全局可变状态。这个方向保证后续路由和服务可共享同一数据契约而不引入循环。

## Migration Contract

1. 按当前定义顺序原样移动 29 个类，仅调整所在模块。
2. `server/schemas.py` 导入 `Any`、`Literal`、`BaseModel` 和 `Field`，并保留 `from __future__ import annotations`。
3. schema 模块使用显式 `__all__` 记录公开名称；`server/app.py` 使用显式 `from .schemas import (...)`，不使用 wildcard 或动态 `globals()` 重导出。
4. `server/app.py` 删除不再使用的 `BaseModel` 和 `Field` 导入；`Literal` 仍被运行时函数注解使用，必须保留，其他 import 与顶层初始化顺序不变。
5. 现有路由注解仍引用 `server.app` 模块全局名称；对 FastAPI 和调用者而言类对象与 schema title 不变。

## Compatibility Checks

- **Python imports**：对每个模型验证 `getattr(server.app, name) is getattr(server.schemas, name)`。
- **OpenAPI**：对 `app.openapi()` 进行稳定 JSON 序列化，校验 path/schema 数量和基线 SHA-256。
- **Pydantic**：现有 API 负面测试继续验证范围、长度、枚举和嵌套验证；不重写第二套字段测试。
- **Runtime**：编译两个模块，直接导入 `server.schemas`、`server.app` 和 ASGI app。

## Tradeoffs

- 选择一个 `schemas.py` 而不是立即按剪辑/艺术字/画中画拆成多个 schema 文件：29 个模型总体仍较小，单模块能先建立依赖方向，避免首次迁移引入过多导入层级。
- 保留 `server.app` 重导出而不强制现有测试立即改用新路径：这是行为保持型迁移，后续可在明确的破坏性变更中删除适配层。
- 不设置类的 `__module__ = "server.app"`：伪造元数据会让序列化和调试指向错误所有者，而当前没有需要这种兼容的证据。

## Rollback

本任务是单提交的结构迁移。回滚时将类定义还原到 `server/app.py`并删除 schema 模块与兼容测试，不需要数据迁移、API 兼容层或用户文件处理。
