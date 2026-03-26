from __future__ import annotations

from typing import Any, Literal, Optional
from typing_extensions import TypedDict



class TableColumn(TypedDict, total=False):
    name: str
    type: str
    nullable: bool
    comment: Optional[str]
    excel_vi_name: Optional[str]
    excel_note: Optional[str]


class TableSchema(TypedDict, total=False):
    table_name: str
    description: Optional[str]
    excel_table_desc: Optional[str]
    columns: list[TableColumn]
    foreign_keys: Optional[list[dict]]
    sample_rows: Optional[list[dict]]


class ChartConfig(TypedDict):
    chart_type: Literal["bar", "line", "pie", "table", "number", "scatter"]
    x_axis: Optional[str]       
    y_axis: Optional[str]      
    group_by: Optional[str]     
    title: str
    x_label: Optional[str]
    y_label: Optional[str]


class SQLCorrectionResult(TypedDict):
    is_valid: bool
    issues: list[str]
    fixed_sql: Optional[str]    



class AgentState(TypedDict, total=False):
    user_query: str                  
    session_id: str                  
    selected_tables: Optional[list[str]]

    intent: Literal[
        "data_query",        
        "chart_request",    
        "schema_question",
        "greeting",
        "out_of_scope",      
        "ambiguous",         
    ]
    intent_reasoning: str            

    relevant_tables: list[str]      
    schema_context: list[TableSchema]  
    pruned_schema_context: list[TableSchema] 
    
    query_plan: str

    generated_sql: str              
    sql_reasoning: str               

    sql_correction: SQLCorrectionResult       
    final_sql: str                  

    query_result: list[dict[str, Any]]  
    row_count: int
    execution_time_ms: float
    executor_error: Optional[str]    

    data_check_is_valid: bool
    data_check_issues: list[str]

    forced_chart_type: Optional[str]        # Hint từ API: ép buộc chart type nếu có
    force_chart: bool                        # Nếu True, luôn sinh chart dù intent không phải chart_request
    column_profiles: Optional[list[dict]]    # Output của data_profiler — phân tích kiểu cột
    chart_config: Optional[ChartConfig] 
    chart_data: Optional[list[dict]]    

    clarification_question: Optional[str]  # Câu hỏi làm rõ khi intent là ambiguous

    answer: str                      
    answer_format: Literal["text", "table", "chart+text"]

    retry_count: int               
    error: Optional[str]           
    next: str                        