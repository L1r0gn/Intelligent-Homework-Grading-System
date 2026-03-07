from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """从字典或列表中获取指定键/索引的值"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    elif isinstance(dictionary, list) and isinstance(key, int):
        try:
            return dictionary[key]
        except IndexError:
            return None
    return None


@register.filter
def last(value):
    """获取列表的最后一个元素"""
    try:
        return value[-1]
    except (TypeError, IndexError):
        return None


@register.filter
def first(value):
    """获取列表的第一个元素"""
    try:
        return value[0]
    except (TypeError, IndexError):
        return None


@register.filter
def enumerate_filter(iterable):
    """返回带索引的枚举列表"""
    return [(i, item) for i, item in enumerate(iterable)]


@register.filter
def multiply(value, arg):
    """乘法运算"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''


@register.filter
def divide(value, arg):
    """除法运算"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def avg(value):
    """计算列表的平均值"""
    try:
        if not value or len(value) == 0:
            return 0
        return sum(value) / len(value)
    except (TypeError, ValueError):
        return 0


@register.filter
def yesno(value, arg=None):
    """根据布尔值返回指定字符串，格式: 'true_value,false_value' 或 'true_value,false_value,null_value'"""
    if arg is None:
        arg = 'yes,no,maybe'
    parts = arg.split(',')
    if len(parts) == 2:
        true_val, false_val = parts
        null_val = false_val
    elif len(parts) == 3:
        true_val, false_val, null_val = parts
    else:
        return value

    if value is None:
        return null_val
    if value:
        return true_val
    return false_val


@register.filter
def subtract(value, arg):
    """减法运算"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """计算百分比"""
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0


@register.filter
def length(value):
    """返回列表长度"""
    try:
        return len(value)
    except (TypeError):
        return 0


@register.filter
def get_trend_class(value):
    """根据趋势值返回CSS类名"""
    try:
        val = float(value)
        if val > 5:
            return 'trend-up-strong'
        elif val > 0:
            return 'trend-up'
        elif val < -5:
            return 'trend-down-strong'
        elif val < 0:
            return 'trend-down'
        else:
            return 'trend-stable'
    except (ValueError, TypeError):
        return 'trend-stable'


@register.filter
def get_mastery_class(value):
    """根据掌握度返回CSS类名"""
    try:
        val = float(value) * 100
        if val >= 80:
            return 'mastery-excellent'
        elif val >= 60:
            return 'mastery-good'
        elif val >= 40:
            return 'mastery-medium'
        else:
            return 'mastery-low'
    except (ValueError, TypeError):
        return 'mastery-low'


@register.simple_tag
def get_trend_icon(value):
    """根据趋势值返回图标HTML"""
    try:
        val = float(value)
        if val > 5:
            return '<i class="fas fa-arrow-up trend-icon-up-strong"></i>'
        elif val > 0:
            return '<i class="fas fa-arrow-up trend-icon-up"></i>'
        elif val < -5:
            return '<i class="fas fa-arrow-down trend-icon-down-strong"></i>'
        elif val < 0:
            return '<i class="fas fa-arrow-down trend-icon-down"></i>'
        else:
            return '<i class="fas fa-minus trend-icon-stable"></i>'
    except (ValueError, TypeError):
        return '<i class="fas fa-minus trend-icon-stable"></i>'


@register.simple_tag
def get_mastery_label(value):
    """根据掌握度返回标签文字"""
    try:
        val = float(value) * 100
        if val >= 80:
            return '优秀'
        elif val >= 60:
            return '良好'
        elif val >= 40:
            return '及格'
        else:
            return '需加强'
    except (ValueError, TypeError):
        return '未知'


@register.simple_tag
def get_study_advice(mastery_level, trend):
    """根据掌握度和趋势生成学习建议"""
    try:
        m_val = float(mastery_level) * 100
        t_val = float(trend)

        if m_val >= 80:
            if t_val > 0:
                return '保持优秀，继续拓展'
            else:
                return '保持领先，温故知新'
        elif m_val >= 60:
            if t_val > 5:
                return '进步明显，再接再厉'
            elif t_val > 0:
                return '稳步提升，继续加油'
            else:
                return '需要巩固，多做练习'
        elif m_val >= 40:
            if t_val > 0:
                return '正在进步，坚持不懈'
            else:
                return '需要加强，重点复习'
        else:
            if t_val > 0:
                return '起步阶段，不要气馁'
            else:
                return '基础薄弱，建议辅导'
    except (ValueError, TypeError):
        return '继续努力'
