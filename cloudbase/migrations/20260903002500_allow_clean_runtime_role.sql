DROP POLICY IF EXISTS clean_app_all ON clean.users;
CREATE POLICY clean_app_all ON clean.users
    FOR ALL TO clean_app
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS clean_app_all ON clean.user_sessions;
CREATE POLICY clean_app_all ON clean.user_sessions
    FOR ALL TO clean_app
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS clean_app_all ON clean.task_reports;
CREATE POLICY clean_app_all ON clean.task_reports
    FOR ALL TO clean_app
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS clean_app_all ON clean.app_settings;
CREATE POLICY clean_app_all ON clean.app_settings
    FOR ALL TO clean_app
    USING (true)
    WITH CHECK (true);
