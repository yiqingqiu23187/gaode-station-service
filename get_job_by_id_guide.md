# get_job_by_id MCP工具使用指南

## 📋 工具概述

`get_job_by_id` 是一个MCP工具，用于根据岗位ID进行精确的岗位属性查询。该工具返回的字段结构与 `find_best_job` 完全一致，确保数据格式的统一性。

## 🎯 主要功能

- **精确查询**: 根据岗位ID获取完整的岗位信息
- **距离计算**: 可选提供用户坐标来计算距离和骑行时间
- **字段一致**: 返回字段与 `find_best_job` 保持一致
- **错误处理**: 完善的错误处理机制

## 📝 参数说明

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `job_id` | `int` | ✅ | 岗位ID，用于精确查询指定岗位 |
| `user_latitude` | `float` | ❌ | 用户纬度坐标，用于计算距离和骑行时间 |
| `user_longitude` | `float` | ❌ | 用户经度坐标，用于计算距离和骑行时间 |

## 📊 返回字段

返回一个包含单个岗位信息的列表，每个岗位包含以下字段：

### 基本信息
- **`job_type`** (str): 岗位类型
- **`recruiting_unit`** (str): 招聘单位  
- **`city`** (str): 城市
- **`gender`** (str): 性别要求
- **`age_requirement`** (str): 年龄要求

### 位置信息
- **`location`** (str): 具体位置地址
- **`longitude`** (float): 岗位经度坐标
- **`latitude`** (float): 岗位纬度坐标

### 工作条件
- **`special_requirements`** (str): 特殊要求
- **`accept_criminal_record`** (str): 是否接受有犯罪记录
- **`urgent_capacity`** (int): 运力紧急情况（1表示紧急，0表示普通）
- **`working_hours`** (str): 工作时间
- **`relevant_experience`** (str): 相关经验要求
- **`full_time`** (str): 是否全职

### 薪资福利
- **`salary`** (str): 薪资信息
- **`insurance_status`** (str): 保险情况
- **`accommodation_status`** (str): 吃住情况

### 工作内容
- **`job_content`** (str): 工作内容描述

### 时间安排
- **`interview_time`** (str): 面试时间
- **`trial_time`** (str): 试岗时间

### 状态信息
- **`currently_recruiting`** (str): 当前是否招聘

### 距离信息（可选）
- **`distance_km`** (float or None): 距离用户的公里数
- **`bicycling_duration_minutes`** (int or None): 骑行时间（分钟）

## 🚀 使用示例

### 示例1: 基本查询（不计算距离）

```python
# 查询ID为1的岗位
result = get_job_by_id(job_id=1)

# 结果示例
[
    {
        "job_type": "白班分拣员",
        "recruiting_unit": "小象超市-白云石井站",
        "city": "广州",
        "gender": "女",
        "age_requirement": "18~35",
        "location": "广州市白云区西槎路989号1栋101号",
        "longitude": 113.235771,
        "latitude": 23.181711,
        "salary": "底薪2340+绩效400+生活补贴0-500+职级补贴(100-700)+计件薪资，综合6000-8000",
        "distance_km": None,
        "bicycling_duration_minutes": None,
        # ... 其他字段
    }
]
```

### 示例2: 带距离计算的查询

```python
# 查询ID为1的岗位，并计算与用户的距离
result = get_job_by_id(
    job_id=1,
    user_latitude=23.1291,    # 广州天河区纬度
    user_longitude=113.3417   # 广州天河区经度
)

# 结果示例
[
    {
        "job_type": "白班分拣员",
        "recruiting_unit": "小象超市-白云石井站",
        "city": "广州",
        "distance_km": 12.31,
        "bicycling_duration_minutes": 49,
        # ... 其他字段
    }
]
```

### 示例3: 查询不存在的岗位

```python
# 查询不存在的岗位ID
result = get_job_by_id(job_id=99999)

# 错误结果示例
[
    {
        "error": "未找到ID为 99999 的岗位"
    }
]
```

## ⚠️ 注意事项

1. **岗位ID必填**: `job_id` 是必需参数，必须提供有效的整数ID
2. **坐标配对**: 如果要计算距离，必须同时提供 `user_latitude` 和 `user_longitude`
3. **返回格式**: 始终返回列表格式，即使只有一个结果
4. **错误处理**: 查询失败时返回包含 `error` 字段的字典
5. **数据库依赖**: 需要确保 `job_positions` 表存在且有数据

## 🔗 相关工具

- **`find_best_job`**: 根据用户位置和性别推荐合适岗位
- **`search_job_by_unit_type`**: 根据招聘单位和岗位类型搜索岗位

## 📊 测试结果

工具已通过完整测试：
- ✅ 基本ID查询功能
- ✅ 带用户坐标的距离计算
- ✅ 不存在ID的错误处理
- ✅ 返回字段完整性验证
- ✅ 与 `find_best_job` 字段结构一致性

## 🏆 使用场景

1. **岗位详情查看**: 当用户选择特定岗位时，获取完整详情
2. **距离评估**: 结合用户位置，评估通勤距离和时间
3. **数据验证**: 验证特定岗位的信息准确性
4. **API集成**: 为前端应用提供精确的岗位查询服务

---

*最后更新时间：2025年9月3日*
