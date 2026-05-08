**标题**: 用户认证模块重构：加盐哈希与数据模型分离

**描述**: 本次 PR 对用户认证模块进行重构，主要变更包括：
1. 新增 User 数据模型（src/models/user.py），将用户实体从业务逻辑中分离
2. 重构密码哈希方案，从无盐 SHA256 升级为加盐哈希，提升安全性
3. 移除遗留的 src/legacy/deprecated.py 中的旧 MD5 哈希实现

**标签**: enhancement, security, breaking-change

**分支**: feature/auth-refactor → main

**作者**: dev_user

**评审者**: security-reviewer, logic-reviewer

**关联 Issue**: #42, #58

**变更概要**: 3 个文件变更（1 新增 + 1 修改 + 1 删除），密码安全等级提升
