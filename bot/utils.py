"""
工具函数模块
"""
import json
import codecs


def decode_unicode_values(values_str):
    """解码 Unicode 编码的 values 字符串"""
    if not values_str:
        return ""
    
    try:
        # 尝试解析 JSON 格式的 Unicode 编码
        if values_str.startswith('"') and values_str.endswith('"'):
            # 移除首尾引号然后解码
            decoded = json.loads(values_str)
            return decoded
        elif '\\u' in values_str:
            # 直接解码 Unicode 转义序列
            decoded = codecs.decode(values_str, 'unicode_escape')
            return decoded
        else:
            # 如果没有编码，直接返回
            return values_str
    except Exception as e:
        print(f"DEBUG: Failed to decode values '{values_str}': {e}")
        return values_str  # 解码失败时返回原始字符串


def format_blood_notification(notice_type, values_str):
    """格式化通知的显示"""
    try:
        # 解码 values
        decoded_values = decode_unicode_values(values_str)
        
        # 检查是否为前三血通知
        if any(blood in notice_type for blood in ['一血', '二血', '三血']):
            # 尝试解析为JSON数组
            if isinstance(decoded_values, str):
                try:
                    values_list = json.loads(decoded_values)
                except:
                    values_list = decoded_values
            else:
                values_list = decoded_values
            
            # 如果是列表格式 ["队伍名", "题目名"]
            if isinstance(values_list, list) and len(values_list) >= 2:
                team_name = values_list[0]
                challenge_name = values_list[1]
                
                # 提取前三血类型和对应表情
                if '一血' in notice_type:
                    blood_type = "一血"
                    emoji = "🥇"
                elif '二血' in notice_type:
                    blood_type = "二血"
                    emoji = "🥈"
                elif '三血' in notice_type:
                    blood_type = "三血"
                    emoji = "🥉"
                else:
                    blood_type = "血腥"
                    emoji = "🏆"
                
                return f"{emoji} 恭喜 {team_name} 获得 [{challenge_name}] {blood_type}"
            else:
                # 如果不是预期格式，返回原始解码值
                return str(decoded_values)
        
        # 检查是否为新题目开放通知
        elif '新题目开放' in notice_type:
            # 解码后的值应该是题目名称
            challenge_name = str(decoded_values) if decoded_values else "未知题目"
            return f"题目 [{challenge_name}] 已开放"
        
        # 检查是否为提示更新通知
        elif '提示更新' in notice_type:
            # 解码后的值应该是题目名称
            challenge_name = str(decoded_values) if decoded_values else "未知题目"
            return f"题目 [{challenge_name}] 更新了提示"
        
        else:
            # 其他通知，直接返回解码后的内容
            return str(decoded_values) if decoded_values else ""
    except Exception as e:
        print(f"DEBUG: Failed to format notification: {e}")
        return str(decoded_values) if decoded_values else ""


def format_challenges_message(game_title: str, challenges_data):
    """格式化题目列表消息"""
    from .config import CATEGORY_MAPPING
    
    text_lines = [f"--- {game_title} -- 题目列表 ---"]
    
    # 按 Category 分组
    category_groups = {}
    for r in challenges_data:
        category = r['Category']
        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(r)
    
    # 按 Category 排序并生成消息
    for category in sorted(category_groups.keys()):
        category_name = CATEGORY_MAPPING.get(category, f"未知类型({category})")
        text_lines.append(f"\n【{category_name}】")
        
        for r in category_groups[category]:
            text_lines.append(f"  {r['Title']} -- {r['OriginalScore']}分")
    
    return "\n".join(text_lines)


def format_ranking_message(game_title: str, ranking_data):
    """格式化排行榜消息"""
    text_lines = [f"{game_title} - 排行榜"]
    text_lines.append("=" * 30)
    
    for row in ranking_data:
        rank_num = row['rank']
        team_name = row['teamname']
        score = row['totalscore']
        
        # 添加排名表情
        if rank_num == 1:
            emoji = "🥇"
        elif rank_num == 2:
            emoji = "🥈"
        elif rank_num == 3:
            emoji = "🥉"
        else:
            emoji = f"{rank_num}."
        
        text_lines.append(f"{emoji} {team_name} -- {score}分")
    
    return "\n".join(text_lines)
