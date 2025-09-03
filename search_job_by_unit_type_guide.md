# search_job_by_unit_type MCP工具说明

## 📋 工具概述

`search_job_by_unit_type` 是一个高德地图服务站点查询系统的MCP工具，用于根据招聘单位和岗位类型在岗位属性表中搜索对应岗位的详细信息。该工具支持模糊搜索，可以灵活地组合搜索条件。

## 🎯 主要功能

- **模糊搜索**：支持招聘单位和岗位类型的部分匹配
- **灵活条件**：可单独或组合使用搜索条件
- **距离计算**：可选提供用户坐标计算到岗位的距离和骑行时间
- **完整信息**：返回与`find_best_job`一致的详细岗位信息

## 📝 参数说明

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|---------|------|
| `recruiting_unit` | str | 否 | None | 招聘单位名称，支持部分匹配（模糊搜索） |
| `job_type` | str | 否 | None | 岗位类型名称，支持部分匹配（模糊搜索） |
| `user_latitude` | float | 否 | None | 用户所在位置的纬度（用于计算距离） |
| `user_longitude` | float | 否 | None | 用户所在位置的经度（用于计算距离） |
| `k` | int | 否 | 100 | 返回的最大岗位数量 |

### ⚠️ 参数要求

- `recruiting_unit` 和 `job_type` 至少需要提供一个
- `user_latitude` 和 `user_longitude` 需要同时提供才能计算距离

## 📤 返回结果

返回一个包含岗位信息的列表，每个岗位包含以下字段：

### 基本信息
- `job_type` (str): 岗位类型
- `recruiting_unit` (str): 招聘单位
- `city` (str): 城市
- `gender` (str): 性别要求
- `age_requirement` (str): 年龄要求

### 工作要求
- `special_requirements` (str): 特殊要求
- `accept_criminal_record` (str): 是否接受有犯罪记录
- `location` (str): 具体位置地址
- `longitude` (float): 岗位经度坐标
- `latitude` (float): 岗位纬度坐标

### 工作条件
- `urgent_capacity` (int): 运力紧急情况（1表示紧急，0表示普通）
- `working_hours` (str): 工作时间
- `relevant_experience` (str): 相关经验要求
- `full_time` (str): 是否全职

### 薪资福利
- `salary` (str): 薪资待遇
- `insurance_status` (str): 保险情况
- `accommodation_status` (str): 吃住情况

### 其他信息
- `job_content` (str): 工作内容
- `interview_time` (str): 面试时间
- `trial_time` (str): 试岗时间
- `currently_recruiting` (str): 当前是否招聘

### 距离信息（可选）
- `distance_km` (float): 距离用户的公里数（提供用户坐标时计算）
- `bicycling_duration_minutes` (int): 骑行时间（分钟，提供用户坐标时计算）

## 💡 使用示例

### 1. 按招聘单位搜索

```python
# 搜索招聘单位包含"石井"的岗位
result = search_job_by_unit_type(recruiting_unit="石井")
```

**搜索逻辑**：模糊匹配，"石井" 可以匹配 "白云石井站"、"石井分站" 等

### 2. 按岗位类型搜索

```python
# 搜索岗位类型包含"分拣"的岗位
result = search_job_by_unit_type(job_type="分拣")
```

**搜索逻辑**：模糊匹配，"分拣" 可以匹配 "白班分拣员"、"夜班分拣员" 等

### 3. 组合条件搜索

```python
# 搜索招聘单位包含"白云"且岗位类型包含"理货"的岗位
result = search_job_by_unit_type(
    recruiting_unit="白云", 
    job_type="理货"
)
```

### 4. 包含距离计算的搜索

```python
# 搜索水产岗位并计算到深圳市中心的距离
result = search_job_by_unit_type(
    job_type="水产",
    user_latitude=22.5431,    # 深圳市中心纬度
    user_longitude=114.0579,  # 深圳市中心经度
    k=10                      # 返回最多10个岗位
)
```

### 5. 限制返回数量

```python
# 只返回前5个匹配的岗位
result = search_job_by_unit_type(
    recruiting_unit="龙华",
    k=5
)
```

## 🔍 模糊搜索特性

### 搜索规则
- 使用 SQL `LIKE` 操作符进行模糊匹配
- 搜索词会被包装为 `%搜索词%` 的形式
- 不区分大小写（依赖数据库配置）

### 搜索示例

| 搜索词 | 可以匹配 |
|--------|----------|
| "石井" | "白云石井站"、"石井分站" |
| "分拣" | "白班分拣员"、"夜班分拣员" |
| "白云" | "白云石井站"、"白云凰岗站"、"白云大道北一站" |
| "员" | "分拣员"、"理货员"、"水产员"、"果切员" |

## 📊 结果排序

### 不提供用户坐标时
1. `urgent_capacity` 降序（紧急岗位优先）
2. `job_type` 升序（岗位类型字母排序）
3. `recruiting_unit` 升序（招聘单位字母排序）

### 提供用户坐标时
1. `urgent_capacity` 降序（紧急岗位优先）
2. `distance_km` 升序（距离近的优先）

## ⚠️ 错误处理

### 常见错误情况

1. **未提供搜索条件**
   ```json
   [{"error": "请至少提供招聘单位或岗位类型中的一个搜索条件"}]
   ```

2. **数据库连接失败**
   ```json
   [{"error": "数据库错误: [具体错误信息]"}]
   ```

3. **表不存在**
   ```json
   [{"error": "job_positions表不存在，请先运行数据库初始化"}]
   ```

## 🎯 使用场景

### 1. 精确单位查找
当已知具体招聘单位名称的一部分时，快速找到该单位的所有岗位。

### 2. 岗位类型筛选
当求职者对特定类型的工作感兴趣时，查找所有相关岗位。

### 3. 区域性搜索
结合地理位置关键词（如"白云"、"龙华"）进行区域性岗位搜索。

### 4. 就近推荐
提供用户当前位置，获取附近的特定类型岗位。

## 📈 性能建议

1. **合理设置返回数量**：使用 `k` 参数限制返回结果，避免过多数据影响性能
2. **精确搜索词**：使用更具体的搜索词可以提高搜索效率
3. **坐标计算**：仅在需要距离信息时才提供用户坐标

## 🔗 相关工具

- `find_best_job`: 基于用户位置和性别推荐最适合的岗位
- `find_nearest_stations`: 查找最近的服务站点

## 📞 技术支持

如遇到问题，请检查：
1. 数据库文件是否存在
2. 搜索参数是否正确
3. 网络连接是否正常（计算骑行时间时需要）

---

*最后更新时间：2025年8月28日*


