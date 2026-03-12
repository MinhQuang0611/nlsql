
.
├─ agents
│  ├─ __init__.py
│  ├─ answer_agent.py
│  ├─ chart_agent.py
│  ├─ executor_agent.py
│  ├─ intent_agent.py
│  ├─ schema_agent.py
│  ├─ sql_check_agent.py
│  └─ sql_gen_agent.py
├─ api
│  ├─ __init__.py
│  ├─ routers
│  │  └─ __init__.py
│  └─ schemas
│     └─ __init__.py
├─ dashboard
│  └─ __init__.py
├─ db
│  ├─ __init__.py
│  ├─ connection.py
│  ├─ migrations
│  │  ├─ env.py
│  │  └─ versions/
│  └─ seeds
│     └─ seed.sql
├─ graph
│  ├─ __init__.py
│  ├─ builder.py
│  ├─ checkpointer.py
│  └─ state.py
├─ prompts
│  ├─ answer.py
│  ├─ chart.py
│  ├─ intent.py
│  ├─ schema_prune.py
│  ├─ sql_check.py
│  └─ sql_gen.py
├─ scripts
│  ├─ export_schema.py
│  ├─ run_bennmark.py
│  └─ test_db_connection.py
├─ api-related / root files
│  ├─ main.py
│  ├─ config.py
│  ├─ docker-compose.yml
│  ├─ Dockerfile
│  ├─ Makefile
│  ├─ requirements.txt
│  ├─ .dockerignore
│  └─ .gitignore

