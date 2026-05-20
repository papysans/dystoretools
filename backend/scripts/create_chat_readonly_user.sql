-- Creates the MySQL user used by the AI chat SQL sandbox.
-- Run as a MySQL administrator after setting a strong password.
--
-- Example:
--   docker compose exec mysql mysql -uroot -p dystore < backend/scripts/create_chat_readonly_user.sql

SET @chat_user = 'chat_readonly';
SET @chat_host = '%';
SET @chat_password = 'CHANGE_ME_STRONG_PASSWORD';

SET @create_user_sql = CONCAT(
  'CREATE USER IF NOT EXISTS ''',
  @chat_user,
  '''@''',
  @chat_host,
  ''' IDENTIFIED BY ''',
  @chat_password,
  ''''
);
PREPARE stmt FROM @create_user_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'chat_readonly'@'%';

-- Intentionally excluded: llm_provider, llm_model, chat_*,
-- app_setting, session_event, alert, scrape_task_run, ai_generation,
-- alembic_version, mysql.*, performance_schema.*, information_schema.*.
GRANT SELECT ON dystore.doudian_order TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.doudian_goods TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.doudian_stock TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.doudian_sku_diagnose TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.goods_diagnose TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.doudian_comment TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.comment_tag_stat TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.comment_index_warn TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.neg_comment_product TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.doudian_aftersale TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.aftersale_counts TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.member_dashboard_agg TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.member_dashboard_day TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.member_dashboard_hist TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.audience_feature TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.member_sales_activity TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.compass_core_data TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.compass_core_trend TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.compass_diagnose TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.compass_industry_word TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.compass_shop_rank TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.shop_video TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.experience_score TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.shop_violation TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.marketing_coupon TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.marketing_activity TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.logistics_event TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.content_video TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.content_live TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.content_imagetext TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.peer_shop TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.peer_goods TO 'chat_readonly'@'%';
GRANT SELECT ON dystore.peer_livestream TO 'chat_readonly'@'%';

FLUSH PRIVILEGES;
