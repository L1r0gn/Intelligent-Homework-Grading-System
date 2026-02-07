# BKT Module Documentation

## 模块概述

BKTModule（贝叶斯知识追踪模块）是智能作业批改系统的核心认知诊断组件，基于经典的BKT（Bayesian Knowledge Tracing）算法实现学生知识掌握度的科学追踪和预测。

### 核心价值
- **精准诊断**: 基于概率模型科学评估学生真实掌握水平
- **动态追踪**: 实时更新学生知识点掌握状态
- **智能预测**: 预测未来学习表现和发展趋势
- **个性化建议**: 为学生和教师提供针对性的学习建议

## 核心功能

### 1. BKT算法引擎
- 实现标准的贝叶斯知识追踪算法
- 支持四个核心参数：初始掌握概率(Prior)、学习转移概率(Learn)、猜测概率(Guess)、失误概率(Slip)
- 提供遗忘衰减机制
- 支持多知识点协同追踪

### 2. 数据模型
- **BKTKnowledgeModel**: 知识点BKT参数模型
- **LearningTrace**: 学习轨迹记录
- **BKTStudentState**: 学生状态追踪
- **BKTClassAnalytics**: 班级层面分析

### 3. 核心服务
- **BKTService**: 主要业务逻辑服务
- **BKTDataMigrationService**: 数据迁移服务
- **BKTParameterInitializationService**: 参数初始化服务

## API接口

### 学生相关接口
```
GET /api/bkt/student/{student_id}/profile/          # 获取学生知识画像
POST /api/bkt/student/{student_id}/prediction/      # 预测学生表现
```

### 班级相关接口
```
GET /api/bkt/class/{class_id}/analytics/            # 获取班级分析数据
```

### 管理接口
```
GET /api/bkt/knowledge-point/{kp_id}/parameters/    # 获取知识点参数
POST /api/bkt/process-learning-event/               # 处理学习事件
POST /api/bkt/migrate-data/                         # 数据迁移
```

## 部署步骤

### 1. 数据库迁移
```bash
python manage.py makemigrations BKTModule
python manage.py migrate
```

### 2. 数据初始化
```python
# 在Django shell中执行
from BKTModule.data_migration import BKTDataMigrationService

# 迁移现有数据
BKTDataMigrationService.migrate_existing_knowledge_points()
BKTDataMigrationService.migrate_existing_submissions()
BKTDataMigrationService.initialize_student_states()
```

### 3. 参数训练
```python
from BKTModule.data_migration import BKTParameterInitializationService
BKTParameterInitializationService.train_parameters_from_history()
```

## 集成说明

### 与现有系统的集成点

1. **作业批改完成后触发**
```python
# 在gradingModule/tasks.py中，在批改完成后调用
from BKTModule.services import BKTService

# 对于每道题的每个知识点
BKTService.process_learning_event(
    student_id=submission.student.id,
    knowledge_point_id=knowledge_point.id,
    is_correct=(submission.status == 'ACCEPTED'),
    submission_id=submission.id
)
```

2. **替代原有的掌握度计算**
```python
# 原来的简单统计方法
# MasteryService.calculate_mastery()

# 新的BKT方法
BKTService.process_learning_event(...)  # 自动更新掌握概率
```

## 性能优化

### 缓存策略
- 学生状态缓存（Redis）
- 班级分析结果缓存
- BKT参数缓存

### 批量处理
- 支持批量学习事件处理
- 异步计算队列
- 数据库查询优化

## 监控和日志

### 关键指标监控
- BKT计算准确性
- 系统响应时间
- 数据一致性检查

### 日志记录
```python
import logging
logger = logging.getLogger('bkt_module')
```

## 测试体系

### 自动化测试
```bash
# 运行全部测试
python manage.py test BKTModule

# 运行特定测试类
python manage.py test BKTModule.tests.BKTAlgorithmTest

# 生成测试覆盖率报告
coverage run --source='BKTModule' manage.py test BKTModule
coverage report -m
```

### 测试覆盖范围
```python
# 单元测试
- BKT算法正确性验证
- 概率计算边界条件测试
- 参数有效性检查

# 集成测试
- 与Django ORM集成测试
- API接口功能测试
- 权限控制验证

# 性能测试
- 大批量学习事件处理
- 并发访问压力测试
- 缓存效果验证

# 回归测试
- 历史bug修复验证
- 兼容性测试
```

## 故障排除指南

### 常见问题诊断

#### 1. 参数异常问题
```python
# 诊断脚本
class ParameterDiagnostics:
    @staticmethod
    def check_all_parameters():
        """全面检查BKT参数"""
        issues = []
        
        # 检查参数范围
        invalid_range = BKTKnowledgeModel.objects.exclude(
            p_L0__range=(0, 1)
        ).exclude(
            p_T__range=(0, 1)
        )
        
        # 检查参数逻辑关系
        illogical_params = BKTKnowledgeModel.objects.filter(
            p_G__gte=0.5  # 猜测概率过高
        )
        
        return {
            'invalid_range': invalid_range,
            'illogical_params': illogical_params
        }
```

#### 2. 性能问题排查
```python
# 性能监控脚本
class PerformanceDiagnostics:
    @staticmethod
    def analyze_slow_queries():
        """分析慢查询"""
        from django.db import connection
        
        # 启用查询日志
        # 分析执行计划
        # 识别性能瓶颈
        pass
    
    @staticmethod
    def cache_effectiveness():
        """评估缓存效果"""
        from django.core.cache import cache
        
        # 统计缓存命中率
        # 分析缓存失效模式
        pass
```

#### 3. 数据一致性检查
```python
# 数据完整性验证
class DataConsistencyChecker:
    @staticmethod
    def verify_student_states():
        """验证学生状态数据一致性"""
        inconsistencies = []
        
        # 检查状态与轨迹的一致性
        for state in BKTStudentState.objects.all():
            trace_count = state.learning_traces.count()
            if state.total_attempts != trace_count:
                inconsistencies.append({
                    'student': state.student_id,
                    'knowledge_point': state.knowledge_point_id,
                    'state_attempts': state.total_attempts,
                    'trace_count': trace_count
                })
        
        return inconsistencies
```

### 应急处理流程
1. **问题识别**: 通过监控告警或用户反馈发现问题
2. **影响评估**: 评估问题对系统功能的影响范围
3. **临时方案**: 实施临时解决方案保证基本功能
4. **根本解决**: 彻底修复问题并验证
5. **预防措施**: 完善监控和预防机制

## 扩展开发指南

### BKT算法扩展
可在`bkt_engine.py`中扩展：
- 多层BKT模型
- 时间敏感BKT
- 个性化参数调整

### 新增分析功能
- 学习路径分析
- 知识点依赖关系网络
- 预测性干预建议

## 版本发布历史

### v2.0.0 (当前版本)
- 完整BKT算法实现
- 多知识点支持
- 班级分析功能
- RESTful API接口
- 性能优化机制

### v1.2.0
- 班级层面分析
- 知识点统计功能

### v1.1.0
- 多知识点题目支持
- 算法性能优化

### v1.0.0
- 基础BKT功能实现
- 核心数据模型

---
*更多技术细节请参考源代码注释和API文档*