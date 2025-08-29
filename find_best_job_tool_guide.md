# find_best_job MCP工具说明

## 工具概述
`find_best_job` 是一个智能岗位推荐工具，根据用户的地理位置和性别信息，从岗位数据库中筛选并推荐最合适的工作岗位。工具输出完整的岗位档案信息，包含23个详细字段，支持智能排序和实时骑行时间计算。

## 调用格式
```
find_best_job(user_latitude, user_longitude, user_gender, k=2000)
```

## 输入参数

```json
{
  "user_latitude": {
    "type": "float",
    "required": true,
    "description": "用户位置纬度坐标"
  },
  "user_longitude": {
    "type": "float", 
    "required": true,
    "description": "用户位置经度坐标"
  },
  "user_gender": {
    "type": "string",
    "required": true,
    "options": ["男", "女", "不限"],
    "description": "用户性别"
  },
  "k": {
    "type": "int",
    "required": false,
    "default": 2000,
    "description": "返回岗位数量上限"
  }
}
```

## 输出格式
返回岗位列表，每个岗位包含以下字段（共23个字段）：

```json
{
  "job_type": "岗位类型",
  "recruiting_unit": "招聘单位",
  "city": "城市",
  "gender": "性别要求",
  "age_requirement": "年龄要求",
  "special_requirements": "特殊要求",
  "accept_criminal_record": "是否接受有犯罪记录",
  "location": "工作地点地址",
  "longitude": 113.264435,
  "latitude": 23.129163,
  "urgent_capacity": 1,
  "working_hours": "工作时间",
  "relevant_experience": "相关经验要求",
  "full_time": "全职",
  "salary": "薪资",
  "job_content": "工作内容",
  "interview_time": "面试时间",
  "trial_time": "试岗时间",
  "currently_recruiting": "当前是否招聘",
  "insurance_status": "保险情况",
  "accommodation_status": "吃住情况",
  "distance_km": 6.54,
  "bicycling_duration_minutes": 47
}
```

## 核心功能

### 智能筛选
- 自动过滤非招聘状态岗位
- 根据性别要求智能匹配
- 只返回有效地理位置的岗位

### 智能排序  
- 紧急岗位(`urgent_capacity=1`)自动置顶
- 按距离远近排序推荐

### 距离计算
- `distance_km`: 直线距离（公里）
- `bicycling_duration_minutes`: 实际骑行时间（分钟）

### 完整字段说明

**基本信息（8个字段）**：
- `job_type`: 岗位类型（如：夜班理货员、水产员）
- `recruiting_unit`: 招聘单位（如：白云石井站）
- `city`: 所在城市
- `location`: 详细工作地址
- `longitude`: 岗位经度坐标
- `latitude`: 岗位纬度坐标
- `gender`: 性别要求（男/女/不限）
- `age_requirement`: 年龄要求

**岗位要求（4个字段）**：
- `special_requirements`: 特殊要求
- `accept_criminal_record`: 是否接受有犯罪记录
- `relevant_experience`: 相关经验要求
- `full_time`: 是否全职

**工作详情（5个字段）**：
- `working_hours`: 详细工作时间
- `salary`: 薪资结构
- `job_content`: 具体工作内容
- `urgent_capacity`: 紧急程度（1=紧急，0=普通）
- `currently_recruiting`: 当前招聘状态

**面试试岗（2个字段）**：
- `interview_time`: 面试时间
- `trial_time`: 试岗时间

**福利待遇（2个字段）**：
- `insurance_status`: 保险情况
- `accommodation_status`: 吃住情况

**地理信息（2个字段）**：
- `distance_km`: 直线距离
- `bicycling_duration_minutes`: 骑行时间

## 使用示例

### 基础调用
```
find_best_job(23.129163, 113.264435, "不限", 5)
```
查找广州附近5个岗位，性别不限

### 精确匹配
```  
find_best_job(22.543099, 114.057868, "男", 10)
```
查找深圳附近10个适合男性的岗位

## Agent使用指南

### 何时使用此工具
- 用户询问附近工作机会
- 需要根据位置推荐岗位
- 用户提到求职、找工作
- 询问通勤时间、距离

### 如何解读结果
- `urgent_capacity=1` 表示紧急招聘岗位，优先推荐
- `distance_km` 提供直线距离参考
- `bicycling_duration_minutes` 提供实际通勤时间
- 结果已按紧急程度和距离自动排序
- 所有字段都包含完整岗位档案信息

### 常见应答模式
```
为您找到 X 个合适的岗位：

🔴 紧急招聘：[job_type] - [recruiting_unit] ([city])
   📍 位置：[location]  
   🚴 骑行：[bicycling_duration_minutes]分钟 (距离[distance_km]km)
   👤 要求：[gender] [age_requirement]
   💰 薪资：[salary]
   ⏰ 工作时间：[working_hours]
   💼 经验：[relevant_experience]
   🏠 福利：[insurance_status] | [accommodation_status]
   
🟢 普通招聘：[job_type] - [recruiting_unit] ([city])
   📍 位置：[location]
   🚴 骑行：[bicycling_duration_minutes]分钟
   💰 薪资：[salary]
   💼 工作内容：[job_content]
   🕐 面试：[interview_time]
```



### 错误处理
- 如果返回错误信息，提示用户检查位置坐标
- API调用失败时，骑行时间显示为0，仍可参考直线距离
- 无结果时，建议扩大搜索范围或调整性别条件

## 注意事项
- 骑行时间通过高德地图API实时计算
- 建议优先推荐骑行时间≤30分钟的岗位
- 紧急岗位通常有更好的待遇和机会
- 工具输出21个完整字段，提供全面的岗位信息
- 支持性别智能筛选和地理位置排序

## 技术实现细节

### 筛选逻辑
1. 剔除所有 `currently_recruiting != '是'` 的岗位
2. 根据用户性别筛选合适岗位
3. 根据经纬度计算距离并排序
4. 紧急岗位置顶，普通岗位按距离排序

### API集成
- 使用高德地图骑行路径规划API
- 包含重试机制和错误处理
- 支持API限制情况下的降级处理

### 数据来源
- 基于 `job_positions` 数据库表（22个字段）
- 输出完整的岗位档案信息（23个字段）
- 实时计算地理距离和骑行时间
- 支持248个站点和8个岗位类型

### 版本更新记录
- **v2.1** - 新增岗位经纬度字段（longitude、latitude）
- **v2.0** - 优化输出字段，新增10个岗位详情字段
- **v1.1** - 添加骑行时间计算功能
- **v1.0** - 基础岗位推荐功能

### 性能特点
- **完整性**: 输出所有岗位数据库字段
- **准确性**: 实时API计算骑行时间
- **智能性**: 多维度筛选和排序
- **实用性**: 丰富的岗位档案信息
