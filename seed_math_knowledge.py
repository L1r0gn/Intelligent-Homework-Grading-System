import os
import django

# === 1. 设置 Django 环境 ===
# 确保这里的 'IntelligentHomeworkGradingSystem' 替换为你实际的项目名称文件夹名
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IntelligentHomeworkGradingSystem.settings')
django.setup()

from questionManageModule.models import Subject, KnowledgePoint


def seed_math_knowledge():
    print("🚀 开始初始化数学知识点体系...")

    # === 2. 确保数学科目存在 ===
    subject, created = Subject.objects.get_or_create(
        name="数学",
        defaults={'code': 'MATH', 'description': '涵盖代数、几何、分析、统计等全领域数学知识'}
    )
    if created:
        print(f"✅ 创建新科目: {subject.name}")
    else:
        print(f"ℹ️ 找到已有科目: {subject.name}")

    # === 3. 定义完整的数学知识点体系 (分类 -> 知识点列表) ===
    # 这种结构方便管理，我们将“分类”写入知识点的 description 中作为标签

    math_structure = {
        "集合与常用逻辑用语": [
            "集合的概念与表示",
            "集合的基本关系(子集/相等)",
            "集合的基本运算(交/并/补)",
            "充分条件与必要条件",
            "全称量词与存在量词"
        ],
        "函数与导数": [
            "函数的概念(定义域/值域)",
            "函数的单调性与最值",
            "函数的奇偶性与周期性",
            "指数与指数函数",
            "对数与对数函数",
            "幂函数",
            "函数的零点与二分法",
            "导数的概念与几何意义",
            "导数的四则运算",
            "利用导数研究函数的单调性",
            "利用导数研究函数的极值与最值"
        ],
        "三角函数": [
            "任意角与弧度制",
            "三角函数的定义",
            "同角三角函数的基本关系",
            "诱导公式",
            "三角函数的图像与性质",
            "函数y=Asin(ωx+φ)的图像变换",
            "两角和与差的正弦/余弦/正切公式",
            "二倍角公式与半角公式",
            "正弦定理与余弦定理",
            "解三角形应用"
        ],
        "平面向量": [
            "平面向量的概念",
            "平面向量的线性运算",
            "平面向量的数量积(点积)",
            "平面向量的坐标表示",
            "向量平行与垂直的判定"
        ],
        "数列": [
            "数列的概念与通项公式",
            "等差数列及其前n项和",
            "等比数列及其前n项和",
            "数列求和的常见方法(裂项相消/错位相减)"
        ],
        "不等式": [
            "不等式的性质",
            "一元二次不等式",
            "基本不等式(均值不等式)",
            "简单的线性规划"
        ],
        "立体几何": [
            "空间几何体的结构与三视图",
            "空间几何体的表面积与体积",
            "平面的基本性质",
            "直线与平面的平行判定与性质",
            "直线与平面的垂直判定与性质",
            "平面与平面的平行/垂直判定",
            "异面直线及其夹角",
            "二面角",
            "空间向量在立体几何中的应用"
        ],
        "解析几何": [
            "直线的倾斜角与斜率",
            "直线的点斜式/一般式方程",
            "两条直线的位置关系(平行/垂直/交点)",
            "点到直线的距离公式",
            "圆的标准方程与一般方程",
            "直线与圆的位置关系",
            "椭圆的定义与标准方程",
            "椭圆的几何性质",
            "双曲线的定义与标准方程",
            "双曲线的几何性质",
            "抛物线的定义与标准方程",
            "抛物线的几何性质"
        ],
        "概率与统计": [
            "随机抽样(简单随机/分层/系统)",
            "频率分布直方图",
            "样本特征数(平均数/方差/标准差)",
            "古典概型",
            "几何概型",
            "互斥事件与对立事件",
            "条件概率与全概率公式",
            "离散型随机变量及其分布列",
            "二项分布",
            "正态分布"
        ],
        "复数": [
            "复数的概念(实部/虚部/模)",
            "复数的几何意义",
            "复数的四则运算"
        ]
    }

    # === 4. 循环插入数据库 ===
    total_added = 0
    total_skipped = 0

    for category, points in math_structure.items():
        print(f"\n📂 正在处理分类: 【{category}】...")
        for point_name in points:
            # 使用 get_or_create 防止重复添加
            obj, created = KnowledgePoint.objects.get_or_create(
                subject=subject,
                name=point_name,
                defaults={
                    'description': f'{category} - 高中数学核心考点'
                }
            )

            if created:
                print(f"  + 新增: {point_name}")
                total_added += 1
            else:
                # print(f"  . 跳过: {point_name} (已存在)")
                total_skipped += 1

    print("-" * 50)
    print(f"🎉 初始化完成！")
    print(f"📊 统计结果: 新增 {total_added} 个, 跳过 {total_skipped} 个")
    print("-" * 50)


if __name__ == '__main__':
    try:
        seed_math_knowledge()
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        print("提示: 请确保你已经在 settings.py 中正确配置了数据库，并运行了 migrations。")