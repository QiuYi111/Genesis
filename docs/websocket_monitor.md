# WebSocket Monitor（W2）

最小 WebSocket 广播器，便于本地或 Web UI 实时观察 `snapshot()` 帧数据。

## 端点与协议

- 地址：`ws://127.0.0.1:<port>/ws`
- 消息：服务端按回合调用 `broadcast(snapshot: dict)` 发送一条 JSON 文本消息；客户端按文本协议接收。
- 心跳：简化实现，无专用心跳帧；`websockets` 会维护 ping/pong（见实现参数）。

当环境未安装 `websockets` 库时，Monitor 自动降级为 no-op，以保证 CLI 不因依赖缺失而失败。

## API（服务端）

- `await start(port: int) -> None`
  - 在指定端口启动服务器并监听路径 `/ws`。
- `await broadcast(snapshot: dict) -> None`
  - 将一帧 JSON 文本广播给所有已连接客户端；内部容错处理单个客户端失败。
- `await stop() -> None`
  - 关闭服务器并释放资源。

实现见：`sociology_simulation/services/web/monitor.py`。

## CLI 集成

- 运行示例（30 回合，默认 null provider）：
  - `uv run python -m sociology_simulation.main world.num_agents=10 runtime.turns=30 model.provider=null`
- 导出到文件（可与 WS 同时使用）：
  - `uv run python -m sociology_simulation.main world.num_agents=10 runtime.turns=10 web.export=true web.export_dir=web_data`

## 客户端示例（浏览器 JavaScript）

```html
<script>
  const ws = new WebSocket('ws://127.0.0.1:8081/ws');
  ws.onmessage = (evt) => {
    const frame = JSON.parse(evt.data);
    // 例如：渲染资源热力图或智能体位置
    console.log('turn', frame.turn, 'agents', frame.agents.length);
  };
</script>
```

## 调试建议

- 首次联调可在浏览器控制台直接连接并打印数据；若未安装 `websockets`，服务端将静默降级为 no-op（无消息）。
- 端口被占用会抛出异常；请更换端口或关闭冲突服务。
- 生产/演示环境建议加上限流、认证与更健壮的心跳机制。

