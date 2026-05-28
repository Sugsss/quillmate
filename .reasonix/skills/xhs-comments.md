# 评论管理与自动回复 Skill

当用户说"查看评论"、"回复评论"、"生成回复"时，使用此 Skill。

## 功能
1. 查看各篇笔记的评论列表
2. AI 自动生成回复建议
3. 支持人工审核后发送或标记为已回复
4. 预留自动回复能力

## 使用方式
调用 API：
- GET /comments/list?publish_id={id} — 查看某篇笔记的评论
- POST /comments/{comment_id}/suggest-reply — AI 生成回复建议
- PUT /comments/{comment_id}/status — 更新回复状态
- POST /comments/add — 手动添加评论（用于模拟数据）

## 工作流程
1. 用户查看某篇笔记的评论列表
2. 对于每条待回复评论，调用 AI 生成回复建议
3. 用户审核建议，满意则标记为"已回复"
4. 未来可扩展为自动回复（需平台API支持）

## 自动回复开关（预留）
在 config 中设置 AUTO_REPLY_ENABLED=true 时，系统可自动用 AI 生成的建议回复新评论。
当前默认关闭（AUTO_REPLY_ENABLED=false），需要人工审核。
