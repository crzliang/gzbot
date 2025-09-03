"""
数据库操作模块
"""
import asyncpg
from .config import POSTGRES_DSN, TARGET_GAME_ID


async def get_game_title(game_id: int) -> str:
    """根据赛事ID获取赛事标题"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        game_record = await conn.fetchrow('SELECT "Title" FROM "Games" WHERE "Id" = $1', game_id)
        if not game_record:
            raise ValueError(f"未找到ID为 {game_id} 的比赛")
        return game_record['Title']
    finally:
        await conn.close()


async def get_game_challenges(game_id: int):
    """获取比赛题目列表"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        rows = await conn.fetch(
            'SELECT "Title", "Category", "OriginalScore" FROM "GameChallenges" WHERE "GameId" = $1 ORDER BY "Id" DESC',
            game_id
        )
        return rows
    finally:
        await conn.close()


async def get_game_rankings(game_id: int):
    """获取比赛排行榜"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        # 最简化的查询，只获取排名、团队名、总分和学号
        query = """
        -- 按每队每题只计一次（取最早 Accepted），同分时按最后被记分时间升序排列（越早越靠前）
        WITH first_accept_per_part AS (
            SELECT
                s."ParticipationId",
                s."ChallengeId",
                MIN(s."SubmitTimeUtc") AS first_time
            FROM "Submissions" s
            WHERE s."GameId" = $1
            AND s."Status" = 'Accepted'
            GROUP BY s."ParticipationId", s."ChallengeId"
        ),
        accepted_per_team AS (
            SELECT
                p."TeamId",
                f."ChallengeId",
                f.first_time
            FROM "Participations" p
            JOIN first_accept_per_part f ON f."ParticipationId" = p."Id"
            WHERE p."GameId" = $1
            AND p."Status" = 1
        ),
        team_scores AS (
            SELECT
                t."Name" AS teamname,
                t."Id" AS teamid,
                COALESCE(SUM(gc."OriginalScore"::integer), 0) AS totalscore,
                -- 团队的最后被记分时间：所有被记分题目的最晚 first_time
                MAX(apt.first_time) AS lastacceptedsubmission
            FROM "Teams" t
            JOIN "Participations" p ON p."TeamId" = t."Id" AND p."GameId" = $1 AND p."Status" = 1
            LEFT JOIN (
                SELECT DISTINCT "TeamId", "ChallengeId", first_time FROM accepted_per_team
            ) apt ON apt."TeamId" = t."Id"
            LEFT JOIN "GameChallenges" gc ON gc."Id" = apt."ChallengeId"
            GROUP BY t."Name", t."Id"
            HAVING SUM(COALESCE(gc."OriginalScore"::integer, 0)) > 0
        ),
        ranked_teams AS (
            SELECT
                teamname,
                teamid,
                totalscore,
                lastacceptedsubmission,
                ROW_NUMBER() OVER (
                    ORDER BY totalscore DESC,
                            lastacceptedsubmission ASC NULLS LAST,
                            teamname ASC
                ) AS rank
            FROM team_scores
        )
        SELECT
            rt.rank,
            rt.teamname,
            rt.totalscore,
            STRING_AGG(DISTINCT u."StdNumber", ', ' ORDER BY u."StdNumber") AS studentnumbers
        FROM ranked_teams rt
        JOIN "Participations" p ON p."TeamId" = rt.teamid AND p."GameId" = $1
        JOIN "UserParticipations" up ON up."ParticipationId" = p."Id"
        JOIN "AspNetUsers" u ON u."Id" = up."UserId"
        GROUP BY rt.rank, rt.teamname, rt.totalscore, rt.lastacceptedsubmission
        ORDER BY rt.rank;
        """
        rows = await conn.fetch(query, game_id)
        return rows
    finally:
        await conn.close()


async def get_game_rankings_by_stdnum_prefix(game_id: int, stdnum_prefix: str):
    """获取按学号前缀过滤的比赛排行榜"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        # 查询指定学号前缀的队伍排行榜
        query = """
        WITH first_accept_per_part AS (
            -- 每个参与(Participation)对每题的最早 Accepted
            SELECT
                s."ParticipationId",
                s."ChallengeId",
                MIN(s."SubmitTimeUtc") AS first_time
            FROM "Submissions" s
            WHERE s."GameId" = $1
            AND s."Status" = 'Accepted'
            GROUP BY s."ParticipationId", s."ChallengeId"
        ),
        accepted_per_team_raw AS (
            -- 关联到队伍，仅统计已被接受的参赛资格
            SELECT
                p."TeamId",
                f."ChallengeId",
                f.first_time
            FROM first_accept_per_part f
            JOIN "Participations" p ON p."Id" = f."ParticipationId"
            WHERE p."GameId" = $1
            AND p."Status" = 1
        ),
        accepted_per_team AS (
            -- 防御性去重（同队同题合并为一次，取最早时间）
            SELECT
                "TeamId",
                "ChallengeId",
                MIN(first_time) AS first_time
            FROM accepted_per_team_raw
            GROUP BY "TeamId", "ChallengeId"
        ),
        team_scores AS (
            -- 计算总分与最后一次被记分时间（用于同分排序）
            SELECT
                t."Name" AS teamname,
                t."Id"   AS teamid,
                COALESCE(SUM(gc."OriginalScore"::integer), 0) AS totalscore,
                MAX(a.first_time) AS lastacceptedsubmission
            FROM "Teams" t
            JOIN "Participations" p ON p."TeamId" = t."Id" AND p."GameId" = $1 AND p."Status" = 1
            LEFT JOIN accepted_per_team a ON a."TeamId" = t."Id"
            LEFT JOIN "GameChallenges" gc ON gc."Id" = a."ChallengeId" AND gc."GameId" = $1
            GROUP BY t."Name", t."Id"
            HAVING SUM(COALESCE(gc."OriginalScore"::integer, 0)) > 0
        ),
        filtered_teams AS (
            -- 按学号前缀过滤队伍（任一成员命中即可）
            SELECT DISTINCT
                ts.teamid,
                ts.teamname,
                ts.totalscore,
                ts.lastacceptedsubmission
            FROM team_scores ts
            JOIN "Participations" p ON p."TeamId" = ts.teamid AND p."GameId" = $1
            JOIN "UserParticipations" up ON up."ParticipationId" = p."Id"
            JOIN "AspNetUsers" u ON u."Id" = up."UserId"
            WHERE u."StdNumber" LIKE ($2 || '%')
        ),
        ranked_teams AS (
            SELECT
                teamname,
                teamid,
                totalscore,
                lastacceptedsubmission,
                ROW_NUMBER() OVER (
                    ORDER BY totalscore DESC,
                            lastacceptedsubmission ASC NULLS LAST,
                            teamname ASC
                ) AS rank
            FROM filtered_teams
        )
        SELECT
            rt.rank,
            rt.teamname,
            rt.totalscore,
            STRING_AGG(DISTINCT u."StdNumber", ', ' ORDER BY u."StdNumber") AS studentnumbers
        FROM ranked_teams rt
        JOIN "Participations" p ON p."TeamId" = rt.teamid AND p."GameId" = $1
        JOIN "UserParticipations" up ON up."ParticipationId" = p."Id"
        JOIN "AspNetUsers" u ON u."Id" = up."UserId"
        GROUP BY rt.rank, rt.teamname, rt.totalscore, rt.lastacceptedsubmission
        ORDER BY rt.rank;
        """
        rows = await conn.fetch(query, game_id, stdnum_prefix)
        return rows
    finally:
        await conn.close()


async def get_recent_notices(game_id: int, seconds: int = 10):
    """获取最近的赛事通知"""
    from datetime import datetime, timedelta
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        query = """
        SELECT 
            gn."Id",
            gn."Type",
            gn."Values",
            gn."PublishTimeUtc",
            CASE gn."Type"
                WHEN 0 THEN '📢 公告通知'
                WHEN 1 THEN '🥇 一血通知'
                WHEN 2 THEN '🥈 二血通知'
                WHEN 3 THEN '🥉 三血通知'
                WHEN 4 THEN '💡 提示更新'
                WHEN 5 THEN '🆕 新题目开放'
                ELSE '❓ 未知类型'
            END as notice_type
        FROM "GameNotices" gn
        WHERE gn."GameId" = $1
          AND gn."PublishTimeUtc" > $2
        ORDER BY gn."PublishTimeUtc" DESC;
        """
        
        time_ago = datetime.utcnow() - timedelta(seconds=seconds)
        rows = await conn.fetch(query, game_id, time_ago)
        return rows
    finally:
        await conn.close()


async def get_challenge_info_by_name(game_id: int, challenge_name: str):
    """根据题目名称获取题目信息"""
    import json
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        # 首先尝试直接匹配
        query = """
        SELECT 
            gc."Title",
            gc."Category",
            CASE gc."Category"
                WHEN 0 THEN 'Misc'
                WHEN 1 THEN 'Crypto'
                WHEN 2 THEN 'Pwn'
                WHEN 3 THEN 'Web'
                WHEN 4 THEN 'Reverse'
                WHEN 5 THEN 'Blockchain'
                WHEN 6 THEN 'Forensics'
                WHEN 7 THEN 'Hardware'
                WHEN 8 THEN 'Mobile'
                WHEN 9 THEN 'PPC'
                WHEN 10 THEN 'AI'
                WHEN 11 THEN 'Pentest'
                WHEN 12 THEN 'OSINT'
                ELSE 'Unknown'
            END as CategoryName
        FROM "GameChallenges" gc
        WHERE gc."GameId" = $1 AND gc."Title" = $2
        LIMIT 1;
        """
        
        # 处理 Values 字段中的题目名称
        # Values 可能是 JSON 格式如 ["题目名"] 或直接是题目名
        actual_challenge_name = challenge_name
        
        # 如果是 JSON 数组格式，提取第一个元素
        if challenge_name.startswith('[') and challenge_name.endswith(']'):
            try:
                parsed_values = json.loads(challenge_name)
                if isinstance(parsed_values, list) and len(parsed_values) > 0:
                    actual_challenge_name = str(parsed_values[0])
            except json.JSONDecodeError:
                pass  # 如果解析失败，使用原始名称
        
        
        
        result = await conn.fetchrow(query, game_id, actual_challenge_name)
        return result
    finally:
        await conn.close()
