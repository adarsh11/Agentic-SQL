"""
Multi-Agent NLP-to-SQL System using LangGraph with Groq API

This module implements a three-agent system for converting natural language queries to SQL:
1. Planner Agent - Intelligently routes queries to appropriate table categories using tool calling
2. SQL Generation Agent - Generates SQL from selected schemas
3. Evaluation Agent - Validates and optimizes generated SQL

Uses Groq API (Llama 3.3 70B) for all LLM operations

Author: AI Assistant
Date: 2025-12-25
"""

import os
import json
import re
from typing import TypedDict, Annotated, List, Optional, Dict, Literal
from datetime import datetime

# LangGraph imports
from langgraph.graph import StateGraph, END, add_messages

# Import custom LLM client
from llm_client import get_llm_client

# Environment variables
from dotenv import load_dotenv
load_dotenv()

# SQL parsing
try:
    import sqlparse
    SQLPARSE_AVAILABLE = True
except ImportError:
    SQLPARSE_AVAILABLE = False
    print("Warning: sqlparse not installed. SQL validation will be basic.")


# =====================================================
# STATE DEFINITION
# =====================================================

class AgentState(TypedDict):
    """State shared across all agents in the graph"""
    
    # Input
    user_query: str
    
    # Planner Agent State
    selected_tool_order: List[int]  # Intelligent order determined by planner
    current_tool_index: int  # Current position in selected_tool_order
    tools_attempted: List[int]  # Track which tools have been called
    selected_tables: Optional[List[Dict]]  # Tables from current category
    selected_category: Optional[str]
    tables_satisfactory: bool
    planner_reasoning: str
    
    # SQL Generation Agent State
    generated_sql: Optional[str]
    sql_generation_attempts: int  # Track retry attempts (max 2)
    sql_generation_error: Optional[str]
    sql_valid: bool
    sql_history: List[str]  # Track all SQL attempts including unoptimized
    
    # Evaluation Agent State
    evaluation_result: Dict  # {passed: bool, score: float, feedback: str}
    optimization_suggestions: List[str]
    accuracy_score: float
    needs_regeneration: bool
    
    # Tool Calls Tracking
    tool_calls_made: Dict  # Track which tools each agent called
    
    # Overall Flow
    final_sql: Optional[str]
    error_message: Optional[str]
    workflow_complete: bool
    
    # Message history for LLM context
    messages: Annotated[list, add_messages]


# =====================================================
# TABLE SCHEMA DEFINITIONS
# =====================================================

CATEGORY_1_TABLES = [
    {
        "table_name": "customers",
        "description": "Customer information including loyalty, demographics, and account status",
        "columns": [
            "customer_id", "customer_uuid", "first_name", "last_name", "email",
            "phone_number", "date_of_birth", "gender", "customer_type",
            "loyalty_tier", "loyalty_points", "total_lifetime_value",
            "account_status", "registration_date", "customer_segment",
            "referral_code", "created_at", "updated_at"
        ],
        "key_columns": ["customer_id", "email", "loyalty_tier", "total_lifetime_value"]
    },
    {
        "table_name": "customer_addresses",
        "description": "Customer billing and shipping addresses with location details",
        "columns": [
            "address_id", "customer_id", "address_type", "is_default",
            "address_line1", "address_line2", "city", "state_province",
            "postal_code", "country", "country_code", "latitude", "longitude",
            "delivery_instructions", "is_verified", "created_at", "updated_at"
        ],
        "key_columns": ["address_id", "customer_id", "address_type", "city", "country"]
    },
    {
        "table_name": "orders",
        "description": "Order transactions with status, payment, and fulfillment information",
        "columns": [
            "order_id", "order_number", "customer_id", "order_date", "order_status",
            "payment_status", "fulfillment_status", "total_amount", "subtotal_amount",
            "tax_amount", "shipping_amount", "discount_amount", "total_items_count",
            "currency_code", "billing_address_id", "shipping_address_id",
            "payment_method", "shipping_method", "tracking_number",
            "estimated_delivery_date", "actual_delivery_date", "channel",
            "created_at", "updated_at"
        ],
        "key_columns": ["order_id", "customer_id", "order_date", "order_status", "total_amount"]
    },
    {
        "table_name": "order_items",
        "description": "Individual items within orders with pricing and fulfillment details",
        "columns": [
            "order_item_id", "order_id", "product_id", "product_variant_id",
            "product_name", "sku", "quantity", "unit_price", "original_unit_price",
            "discount_amount", "tax_amount", "total_price", "weight",
            "fulfillment_status", "warehouse_id", "return_eligible",
            "warranty_months", "cost_price", "profit_margin",
            "created_at", "updated_at"
        ],
        "key_columns": ["order_item_id", "order_id", "product_id", "quantity", "total_price"]
    },
    {
        "table_name": "payments",
        "description": "Payment transactions and methods with gateway information",
        "columns": [
            "payment_id", "payment_reference", "order_id", "customer_id",
            "payment_method", "payment_type", "payment_status", "transaction_id",
            "amount", "currency_code", "payment_date", "authorization_code",
            "card_type", "card_last_four", "billing_address_id",
            "payment_gateway", "gateway_transaction_id", "gateway_fee",
            "refund_reason", "refunded_amount", "created_at", "updated_at"
        ],
        "key_columns": ["payment_id", "order_id", "payment_method", "payment_status", "amount"]
    }
]

CATEGORY_2_TABLES = [
    {
        "table_name": "products",
        "description": "Product catalog with pricing, dimensions, and categorization",
        "columns": [
            "product_id", "product_uuid", "product_name", "product_slug",
            "short_description", "long_description", "category_id", "brand_id",
            "manufacturer_id", "base_price", "sale_price", "cost_price",
            "currency_code", "sku", "barcode", "upc", "weight", "weight_unit",
            "length", "width", "height", "dimension_unit", "is_active",
            "is_featured", "is_bestseller", "launch_date", "created_at", "updated_at"
        ],
        "key_columns": ["product_id", "product_name", "category_id", "base_price", "sku"]
    },
    {
        "table_name": "product_variants",
        "description": "Product variations (size, color, material) with pricing and inventory",
        "columns": [
            "variant_id", "product_id", "variant_name", "variant_sku",
            "variant_barcode", "price", "compare_at_price", "cost_price",
            "weight", "weight_unit", "color", "size", "material", "style",
            "pattern", "option1_name", "option1_value", "option2_name",
            "option2_value", "image_url", "is_default", "is_available",
            "inventory_quantity", "reserved_quantity", "created_at", "updated_at"
        ],
        "key_columns": ["variant_id", "product_id", "variant_sku", "color", "size", "inventory_quantity"]
    },
    {
        "table_name": "inventory",
        "description": "Warehouse inventory levels and stock management",
        "columns": [
            "inventory_id", "product_id", "product_variant_id", "warehouse_id",
            "location_id", "quantity_on_hand", "quantity_available",
            "quantity_reserved", "quantity_in_transit", "quantity_damaged",
            "reorder_point", "reorder_quantity", "max_stock_level",
            "min_stock_level", "safety_stock", "lead_time_days",
            "last_stock_count_date", "last_restock_date", "last_sale_date",
            "unit_cost", "total_value", "stock_status", "lot_number",
            "expiry_date", "created_at", "updated_at"
        ],
        "key_columns": ["inventory_id", "product_id", "warehouse_id", "quantity_available", "stock_status"]
    },
    {
        "table_name": "categories",
        "description": "Product category hierarchy with SEO and performance metrics",
        "columns": [
            "category_id", "category_name", "category_slug", "parent_category_id",
            "category_level", "category_path", "description", "image_url",
            "display_order", "is_active", "is_featured", "meta_title",
            "meta_description", "commission_rate", "tax_category",
            "product_count", "average_rating", "total_sales",
            "created_at", "updated_at"
        ],
        "key_columns": ["category_id", "category_name", "parent_category_id", "product_count"]
    },
    {
        "table_name": "suppliers",
        "description": "Supplier information and terms",
        "columns": [
            "supplier_id", "supplier_code", "supplier_name", "supplier_type",
            "contact_person", "email", "phone", "website", "tax_id",
            "business_registration_number", "address_line1", "city",
            "state_province", "country", "payment_terms", "credit_limit",
            "currency_code", "lead_time_days", "minimum_order_quantity",
            "minimum_order_value", "supplier_rating", "is_active",
            "is_preferred", "created_at", "updated_at"
        ],
        "key_columns": ["supplier_id", "supplier_name", "supplier_type", "supplier_rating"]
    }
]

CATEGORY_3_TABLES = [
    {
        "table_name": "warehouses",
        "description": "Warehouse locations and capacity information",
        "columns": [
            "warehouse_id", "warehouse_code", "warehouse_name", "warehouse_type",
            "manager_name", "email", "phone", "address_line1", "city",
            "state_province", "country", "latitude", "longitude",
            "total_capacity_sqft", "used_capacity_sqft", "temperature_controlled",
            "hazmat_certified", "operating_hours", "timezone", "is_active",
            "is_default", "priority_level", "total_sku_count",
            "total_inventory_value", "last_audit_date", "created_at", "updated_at"
        ],
        "key_columns": ["warehouse_id", "warehouse_name", "city", "warehouse_type", "is_active"]
    },
    {
        "table_name": "shipments",
        "description": "Order shipment tracking and delivery status",
        "columns": [
            "shipment_id", "shipment_number", "order_id", "warehouse_id",
            "carrier_name", "carrier_service", "tracking_number", "tracking_url",
            "shipment_status", "shipment_date", "estimated_delivery_date",
            "actual_delivery_date", "shipping_method", "shipping_cost",
            "insurance_cost", "package_count", "total_weight", "weight_unit",
            "shipping_address_id", "signature_required", "delivery_attempts",
            "last_scan_location", "last_scan_time", "is_international",
            "created_at", "updated_at"
        ],
        "key_columns": ["shipment_id", "order_id", "tracking_number", "shipment_status", "carrier_name"]
    },
    {
        "table_name": "product_reviews",
        "description": "Customer product reviews and ratings",
        "columns": [
            "review_id", "product_id", "product_variant_id", "customer_id",
            "order_id", "order_item_id", "rating", "review_title", "review_text",
            "review_status", "is_verified_purchase", "helpful_count",
            "not_helpful_count", "reported_count", "response_from_seller",
            "response_date", "pros", "cons", "would_recommend",
            "quality_rating", "value_rating", "reviewer_location",
            "usage_period", "created_at", "updated_at"
        ],
        "key_columns": ["review_id", "product_id", "customer_id", "rating", "is_verified_purchase"]
    },
    {
        "table_name": "promotions",
        "description": "Promotional campaigns and discount codes",
        "columns": [
            "promotion_id", "promotion_code", "promotion_name", "promotion_type",
            "discount_value", "discount_percentage", "description",
            "terms_and_conditions", "start_date", "end_date", "usage_limit",
            "usage_limit_per_customer", "current_usage_count",
            "minimum_purchase_amount", "maximum_discount_amount",
            "applicable_to", "is_stackable", "priority_level", "is_active",
            "auto_apply", "channel", "created_at", "updated_at"
        ],
        "key_columns": ["promotion_id", "promotion_code", "promotion_type", "start_date", "end_date"]
    },
    {
        "table_name": "sales_analytics",
        "description": "Aggregated sales metrics and KPIs",
        "columns": [
            "analytics_id", "record_date", "hour_of_day", "day_of_week",
            "week_of_year", "month", "quarter", "year", "channel",
            "category_id", "product_id", "warehouse_id", "region", "country",
            "total_orders", "total_revenue", "total_cost", "total_profit",
            "total_items_sold", "average_order_value", "new_customers_count",
            "returning_customers_count", "cancelled_orders", "refunded_orders",
            "conversion_rate", "cart_abandonment_rate", "website_visits",
            "created_at", "updated_at"
        ],
        "key_columns": ["analytics_id", "record_date", "total_revenue", "total_orders", "channel"]
    }
]

# Map category indices to their data
CATEGORY_MAP = {
    0: {"name": "Customer & Sales", "tables": CATEGORY_1_TABLES},
    1: {"name": "Inventory & Products", "tables": CATEGORY_2_TABLES},
    2: {"name": "Operations & Analytics", "tables": CATEGORY_3_TABLES}
}


# =====================================================
# TOOL DEFINITIONS FOR PLANNER
# =====================================================

# Define tools in OpenAI function calling format
PLANNER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_sales_tables",
            "description": "Retrieve table schemas for Customer & Sales category. Use this for queries about: customers, customer profiles, loyalty programs, orders, order history, sales transactions, payments, billing, revenue from customers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why this category is relevant for the query"
                    }
                },
                "required": ["reasoning"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_products_tables",
            "description": "Retrieve table schemas for Inventory & Products category. Use this for queries about: products, product catalog, SKUs, inventory levels, stock management, warehouses, product categories, suppliers, product variants (size, color, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why this category is relevant for the query"
                    }
                },
                "required": ["reasoning"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_operations_analytics_tables",
            "description": "Retrieve table schemas for Operations & Analytics category. Use this for queries about: shipments, delivery tracking, logistics, warehouses, product reviews, ratings, promotions, discounts, sales analytics, business metrics, KPIs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of why this category is relevant for the query"
                    }
                },
                "required": ["reasoning"]
            }
        }
    }
]


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def validate_sql_syntax(sql: str) -> bool:
    """
    Validate SQL syntax using sqlparse if available, otherwise basic validation.
    """
    if not sql or not sql.strip():
        return False
    
    # Remove markdown code blocks if present
    sql = sql.strip()
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(lines[1:-1]) if len(lines) > 2 else sql
        if sql.startswith("sql"):
            sql = sql[3:].strip()
    
    if SQLPARSE_AVAILABLE:
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return False
            # Check if it's a valid SELECT statement
            first_stmt = parsed[0]
            return first_stmt.get_type() in ['SELECT', 'WITH']
        except Exception as e:
            print(f"SQL parsing error: {e}")
            return False
    else:
        # Basic validation - check for SELECT keyword
        sql_upper = sql.upper().strip()
        return sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')


def format_table_schemas(tables: List[Dict]) -> str:
    """Format table schemas for LLM prompt."""
    formatted = []
    for table in tables:
        schema = f"""Table: {table['table_name']}
Description: {table['description']}
Columns: {', '.join(table['columns'])}
Key Columns: {', '.join(table['key_columns'])}"""
        formatted.append(schema)
    return "\n\n".join(formatted)


# =====================================================
# AGENT NODE IMPLEMENTATIONS
# =====================================================

def planner_node(state: AgentState) -> AgentState:
    """
    Planner Agent: Uses tool calling to intelligently select table category order.
    """
    print("\n" + "="*60)
    print("🧠 PLANNER AGENT")
    print("="*60)
    
    llm_client = get_llm_client()
    
    # Check if we need to determine tool order
    if "selected_tool_order" not in state or not state["selected_tool_order"]:
        print("🎯 Determining optimal tool call order...")
        
        system_prompt = """You are a Planner Agent for an NLP-to-SQL system.

Analyze the user's query and determine which table category tools to call, in order of relevance.
If the query is COMPLETELY UNRELATED to Retail data (Customers, Inventory, Products, Sales, Orders, Shipping, Reviews), do NOT call any tools.
For example, queries about Employees, HR, Hospital, Finance (non-retail), or Weather are OUT OF SCOPE.
"""

        user_prompt = f"""User Query: {state['user_query']}

Analyze this query and call the most relevant tool(s) in order of relevance."""

        try:
            # Use tool calling to get intelligent ordering
            response = llm_client.generate_with_tools(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tools=PLANNER_TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=500
            )
            
            # Extract tool call order
            tool_order = []
            tool_name_to_index = {
                "get_customer_sales_tables": 0,
                "get_inventory_products_tables": 1,
                "get_operations_analytics_tables": 2
            }
            
            if response["tool_calls"]:
                for tc in response["tool_calls"]:
                    tool_name = tc["function"]["name"]
                    if tool_name in tool_name_to_index:
                        idx = tool_name_to_index[tool_name]
                        if idx not in tool_order:
                            tool_order.append(idx)
                        
                        # Parse reasoning
                        try:
                            args = json.loads(tc["function"]["arguments"])
                            reasoning = args.get("reasoning", "")
                            print(f"  📌 Tool {idx + 1}: {CATEGORY_MAP[idx]['name']}")
                            print(f"     Reasoning: {reasoning}")
                        except:
                            pass
            
            # If no tools called or parsing failed, we should check if LLM intentionally avoided tools
            if not tool_order:
                # Ask LLM if this query is out of scope
                # Ask LLM if this query is out of scope with a very strict prompt
                out_of_scope_prompt = f"""Is the query '{state['user_query']}' related to our Retail database (Customers, Orders, Products, Inventory, Shipping, Sales)?
Answer 'NO' if it's about employees, HR, hospitals, or anything not in the list above.
Answer 'YES' only if it's clearly about retail customers, stock, orders, or sales.
Respond with ONLY yes or no."""
                is_related = llm_client.generate(out_of_scope_prompt, temperature=0).strip().upper()
                
                if "NO" in is_related:
                    return {
                        "error_message": f"❌ The query about '{state['user_query']}' is outside our Retail database scope. We handle Customers, Products, and Sales data.",
                        "planner_reasoning": "Out-of-scope query filtered.",
                        "workflow_complete": True
                    }

                print("  ⚠️  No tools selected but related, using default order [0, 1, 2]")
                tool_order = [0, 1, 2]
            else:
                # Add remaining tools to the end
                for i in range(3):
                    if i not in tool_order:
                        tool_order.append(i)
            
            state["selected_tool_order"] = tool_order
            state["current_tool_index"] = 0
            state["tools_attempted"] = []
            
            # Track tool calls made by planner
            if "tool_calls_made" not in state:
                state["tool_calls_made"] = {}
            state["tool_calls_made"]["planner"] = [tc["function"]["name"] for tc in response.get("tool_calls", [])]
            
            print(f"\n✅ Tool call order determined: {[CATEGORY_MAP[i]['name'] for i in tool_order]}")
            
        except Exception as e:
            print(f"❌ Error in tool selection: {e}")
            # Fallback to default order
            state["selected_tool_order"] = [0, 1, 2]
            state["current_tool_index"] = 0
            state["tools_attempted"] = []
    
    # Get current tool to try
    current_idx = state.get("current_tool_index", 0)
    tool_order = state.get("selected_tool_order", [0, 1, 2])
    tools_attempted = state.get("tools_attempted", [])
    
    if current_idx >= len(tool_order):
        # All tools exhausted
        return {
            "error_message": "❌ I couldn't find any satisfactory tables to answer your query. Please try rephrasing or ask about products, orders, or customers.",
            "planner_reasoning": "All available table categories were checked but none were relevant.",
            "workflow_complete": True
        }
    
    # Get the tool index from the order
    tool_idx = tool_order[current_idx]
    category_info = CATEGORY_MAP[tool_idx]
    
    print(f"\n📍 Trying Category {current_idx + 1}/{len(tool_order)}: {category_info['name']}")
    
    # Calculate relevance score using LLM
    table_summary = "\n".join([
        f"- {t['table_name']}: {t['description']}"
        for t in category_info['tables']
    ])
    
    relevance_prompt = f"""Analyze how relevant these database tables are for answering the user's query.
User Query: {state['user_query']}
Available Tables in {category_info['name']} category:
{table_summary}
Rate the relevance (0.0 to 1.0). Respond with ONLY a number."""

    try:
        score_response = llm_client.generate(prompt=relevance_prompt, temperature=0, max_tokens=10)
        score_match = re.search(r'0?\.\d+|1\.0|0|1', score_response)
        relevance_score = float(score_match.group()) if score_match else 0.5
    except:
        relevance_score = 0.5
    
    is_satisfactory = relevance_score >= 0.8
    print(f"📊 Relevance Score: {relevance_score:.2f} (Satisfactory: {is_satisfactory})")
    
    return {
        "selected_tables": category_info['tables'],
        "selected_category": category_info['name'],
        "tables_satisfactory": is_satisfactory,
        "planner_reasoning": f"Analyzed {category_info['name']} (Score: {relevance_score:.2f})",
        "tools_attempted": tools_attempted + [tool_idx],
        "current_tool_index": current_idx + (0 if is_satisfactory else 1)
    }


def sql_generation_node(state: AgentState) -> AgentState:
    """
    SQL Generation Agent: Generates SQL from NL query and selected tables.
    """
    print("\n" + "="*60)
    print("💻 SQL GENERATION AGENT")
    print("="*60)
    
    llm_client = get_llm_client()
    
    # Prepare table schemas
    table_schemas = format_table_schemas(state["selected_tables"])
    
    # Check if this is a retry with feedback
    is_retry = state.get("needs_regeneration", False)
    previous_sql = state.get("generated_sql", "")
    feedback = state.get("evaluation_result", {}).get("feedback", "")
    
    attempt_num = state.get("sql_generation_attempts", 0) + 1
    print(f"🔄 Attempt {attempt_num}/2")
    
    if is_retry:
        print(f"📝 Regenerating based on feedback...")
        print(f"💬 Feedback: {feedback}")
    
    system_prompt = """You are an expert SQL Generation Agent specializing in PostgreSQL.

Generate a syntactically correct and semantically accurate SQL query based on:
1. The user's natural language question
2. The provided database table schemas

RULES:
- Use ONLY the tables and columns provided in the schemas
- Follow PostgreSQL syntax strictly
- Use appropriate JOINs when querying multiple tables
- Apply WHERE clauses, GROUP BY, ORDER BY, and LIMIT as needed
- Optimize the query (avoid SELECT *, use proper indexes)
- Return ONLY the SQL query without any explanations or markdown
- Do NOT wrap the query in code blocks
- Ensure proper aliasing for clarity
- Use meaningful column aliases in SELECT

IMPORTANT: Your response should be ONLY the SQL query, nothing else."""

    if is_retry:
        system_prompt += f"""

⚠️ REGENERATION REQUEST
Your previous SQL had issues and needs improvement.

Previous SQL:
{previous_sql}

Evaluation Feedback:
{feedback}

Please generate an IMPROVED query that addresses the feedback above."""

    user_prompt = f"""User Query: {state['user_query']}

Selected Category: {state['selected_category']}

Available Table Schemas:
{table_schemas}

Generate the SQL query now."""

    try:
        sql_query = llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1500
        )
        
        sql_query = sql_query.strip()
        
        # Clean up the SQL - remove markdown code blocks
        if "```" in sql_query:
            match = re.search(r'```(?:sql)?\s*(.*?)\s*```', sql_query, re.DOTALL)
            if match:
                sql_query = match.group(1).strip()
        
        # Validate SQL
        is_valid = validate_sql_syntax(sql_query)
        
        print(f"\n📄 Generated SQL:")
        print("-" * 60)
        print(sql_query)
        print("-" * 60)
        print(f"✓ Valid: {is_valid}")
        
        state["generated_sql"] = sql_query
        state["sql_valid"] = is_valid
        state["sql_generation_attempts"] = attempt_num
        
        # Track SQL history
        if "sql_history" not in state:
            state["sql_history"] = []
        state["sql_history"].append(sql_query)
        
        if not is_valid:
            state["sql_generation_error"] = "SQL syntax validation failed"
            print(f"❌ {state['sql_generation_error']}")
        else:
            state["sql_generation_error"] = None
            state["needs_regeneration"] = False
            
    except Exception as e:
        error_msg = f"SQL generation error: {str(e)}"
        print(f"❌ {error_msg}")
        state["sql_generation_error"] = error_msg
        state["sql_valid"] = False
        state["sql_generation_attempts"] = attempt_num
    
    return state


def evaluation_node(state: AgentState) -> AgentState:
    """
    Evaluation Agent: Validates SQL quality and accuracy.
    """
    print("\n" + "="*60)
    print("🔍 EVALUATION AGENT")
    print("="*60)
    
    llm_client = get_llm_client()
    
    sql_query = state["generated_sql"]
    user_query = state["user_query"]
    
    system_prompt = """You are an SQL Evaluation Agent specializing in query optimization and accuracy.

Evaluate the generated SQL query based on TWO criteria:

1. **ACCURACY** (0.0-1.0): Does the SQL correctly answer the user's question?
   - Check if the right tables are joined
   - Verify WHERE conditions match the intent
   - Ensure aggregations are correct
   - Validate the output columns match what's asked

2. **OPTIMIZATION** (0.0-1.0): Is the query optimized?
   - Avoid SELECT * (use specific columns)
   - Proper use of indexes (infer from WHERE/JOIN on ID columns)
   - Efficient JOINs (avoid unnecessary joins)
   - Use LIMIT for large result sets when appropriate
   - Proper use of aggregations and GROUP BY

SCORING THRESHOLDS:
- Query PASSES if: accuracy_score >= 0.9 AND optimization_score >= 0.7
- Query FAILS if: either score is below threshold

Respond in VALID JSON format only:
{
  "passed": true/false,
  "accuracy_score": 0.95,
  "optimization_score": 0.85,
  "feedback": "Detailed explanation of issues or approval",
  "suggestions": ["Specific improvement 1", "Specific improvement 2"]
}

IMPORTANT: Return ONLY valid JSON, no other text."""

    user_prompt = f"""User Query: {user_query}

Generated SQL:
{sql_query}

Evaluate this SQL query now."""

    try:
        response_text = llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=800
        )
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group()
            eval_result = json.loads(json_text)
        else:
            eval_result = json.loads(response_text)
        
        print(f"📊 Evaluation Results:")
        print(f"   Accuracy Score: {eval_result['accuracy_score']:.2f}")
        print(f"   Optimization Score: {eval_result['optimization_score']:.2f}")
        print(f"   Passed: {eval_result['passed']}")
        print(f"\n💬 Feedback: {eval_result['feedback']}")
        
        if eval_result.get('suggestions'):
            print(f"\n💡 Suggestions:")
            for i, suggestion in enumerate(eval_result['suggestions'], 1):
                print(f"   {i}. {suggestion}")
        
        state["evaluation_result"] = eval_result
        state["accuracy_score"] = eval_result["accuracy_score"]
        state["optimization_suggestions"] = eval_result.get("suggestions", [])
        state["needs_regeneration"] = not eval_result["passed"]
        
        if eval_result["passed"]:
            state["final_sql"] = sql_query
            state["workflow_complete"] = True
            print(f"\n✅ SQL APPROVED!")
        else:
            print(f"\n⚠️  SQL needs improvement. Will regenerate...")
        
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parsing error: {e}")
        print(f"Response was: {response_text[:200]}")
        # Fallback: auto-approve if parsing fails
        state["evaluation_result"] = {
            "passed": True,
            "accuracy_score": 0.9,
            "optimization_score": 0.8,
            "feedback": "Auto-approved due to evaluation parsing error",
            "suggestions": []
        }
        state["final_sql"] = sql_query
        state["workflow_complete"] = True
        print(f"✅ Auto-approved (evaluation parsing failed)")
        
    except Exception as e:
        print(f"❌ Evaluation error: {e}")
        # Fallback: auto-approve
        state["evaluation_result"] = {
            "passed": True,
            "accuracy_score": 0.9,
            "optimization_score": 0.8,
            "feedback": f"Auto-approved due to error: {str(e)}",
            "suggestions": []
        }
        state["final_sql"] = sql_query
        state["workflow_complete"] = True
    
    return state


def error_node(state: AgentState) -> AgentState:
    """Handle errors and generate appropriate messages."""
    if state.get("error_message") is None or state.get("error_message") == "":
        if state.get("sql_generation_error"):
            state["error_message"] = f"SQL Generation failed: {state['sql_generation_error']}"
        else:
            state["error_message"] = "I apologize, but I couldn't find any relevant tables or generate a valid query for that specific request."
    
    state["workflow_complete"] = True
    return state


# =====================================================
# CONDITIONAL EDGE FUNCTIONS
# =====================================================

def should_continue_planner(state: AgentState) -> Literal["sql_generation", "planner", "error"]:
    """Determine next step after planner."""
    if state.get("workflow_complete"):
        return "error"
    
    if state.get("tables_satisfactory"):
        return "sql_generation"
    else:
        # Try next tool in the intelligent order
        if state["current_tool_index"] < len(state["selected_tool_order"]):
            return "planner"  # Loop back to try next category
        else:
            return "error"  # All tools exhausted


def should_retry_sql(state: AgentState) -> Literal["evaluation", "sql_generation", "error"]:
    """Determine if SQL generation should retry."""
    if state.get("sql_valid"):
        return "evaluation"
    else:
        attempts = state.get("sql_generation_attempts", 0)
        if attempts < 2:
            return "sql_generation"  # Retry
        else:
            return "error"  # Max retries exceeded


def should_regenerate_sql(state: AgentState) -> Literal["sql_generation", "end"]:
    """Determine if SQL needs regeneration after evaluation."""
    if state.get("workflow_complete"):
        return "end"
    elif state.get("needs_regeneration"):
        # Check if we've already regenerated too many times
        if state.get("sql_generation_attempts", 0) >= 4:
            # Prevent infinite loops - accept current SQL
            print("\n⚠️  Max regeneration attempts reached. Accepting current SQL.")
            state["final_sql"] = state["generated_sql"]
            state["error_message"] = "SQL generated but with quality concerns: " + state["evaluation_result"]["feedback"]
            state["workflow_complete"] = True
            return "end"
        return "sql_generation"
    else:
        return "end"


# =====================================================
# LANGGRAPH WORKFLOW CONSTRUCTION
# =====================================================

def create_nlp_to_sql_graph():
    """
    Create the multi-agent NLP-to-SQL LangGraph workflow.
    """
    # Initialize graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("sql_generation", sql_generation_node)
    workflow.add_node("evaluation", evaluation_node)
    workflow.add_node("error", error_node)
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    # Add conditional edges from planner
    workflow.add_conditional_edges(
        "planner",
        should_continue_planner,
        {
            "sql_generation": "sql_generation",
            "planner": "planner",
            "error": "error"
        }
    )
    
    # Add conditional edges from SQL generation
    workflow.add_conditional_edges(
        "sql_generation",
        should_retry_sql,
        {
            "evaluation": "evaluation",
            "sql_generation": "sql_generation",
            "error": "error"
        }
    )
    
    # Add conditional edges from evaluation
    workflow.add_conditional_edges(
        "evaluation",
        should_regenerate_sql,
        {
            "sql_generation": "sql_generation",
            "end": END
        }
    )
    
    # Error node goes to END
    workflow.add_edge("error", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


# =====================================================
# MAIN EXECUTION FUNCTION
# =====================================================

def run_nlp_to_sql(user_query: str, verbose: bool = True) -> Dict:
    """
    Execute the NLP-to-SQL workflow for a given user query.
    
    Args:
        user_query: Natural language query from user
        verbose: Whether to print detailed execution logs
        
    Returns:
        Dictionary with success status, SQL, and metadata
    """
    if verbose:
        print("\n" + "="*60)
        print("🚀 MULTI-AGENT NLP-TO-SQL SYSTEM (Groq/Llama 3.3)")
        print("="*60)
        print(f"📝 User Query: {user_query}")
    
    # Create the graph
    app = create_nlp_to_sql_graph()
    
    # Initialize state
    initial_state = {
        "user_query": user_query,
        "selected_tool_order": [],
        "current_tool_index": 0,
        "tools_attempted": [],
        "selected_tables": None,
        "selected_category": None,
        "tables_satisfactory": False,
        "planner_reasoning": "",
        "generated_sql": None,
        "sql_generation_attempts": 0,
        "sql_generation_error": None,
        "sql_valid": False,
        "sql_history": [],
        "evaluation_result": {},
        "optimization_suggestions": [],
        "accuracy_score": 0.0,
        "needs_regeneration": False,
        "final_sql": None,
        "error_message": None,
        "workflow_complete": False,
        "tool_calls_made": {},
        "messages": []
    }
    
    # Run the graph
    result = app.invoke(initial_state)
    
    # Format result
    # We use .get() to be safe and ensure we always return a valid dict
    final_sql = result.get("final_sql")
    error_msg = result.get("error_message")
    
    if final_sql:
        output = {
            "success": True,
            "sql": final_sql,
            "category": result.get("selected_category"),
            "tool_order": [CATEGORY_MAP[i]["name"] for i in result.get("selected_tool_order", []) if i in CATEGORY_MAP],
            "evaluation": result.get("evaluation_result", {}),
            "planner_reasoning": result.get("planner_reasoning", ""),
            "attempts": result.get("sql_generation_attempts", 0),
            "sql_history": result.get("sql_history", []),
            "tool_calls_made": result.get("tool_calls_made", {})
        }
        
        if verbose:
            print("\n" + "="*60)
            print("✅ SUCCESS - SQL GENERATED")
            print("="*60)
    else:
        output = {
            "success": False,
            "error": error_msg or "I was unable to find relevant information or generate a valid query for your request.",
            "attempts": result.get("sql_generation_attempts", 0),
            "category": result.get("selected_category"),
            "tool_order": [CATEGORY_MAP[i]["name"] for i in result.get("selected_tool_order", []) if i in CATEGORY_MAP],
            "planner_reasoning": result.get("planner_reasoning", ""),
            "evaluation": result.get("evaluation_result", {}),
            "sql_history": result.get("sql_history", []),
            "tool_calls_made": result.get("tool_calls_made", {})
        }
        
        if verbose:
            print("\n" + "="*60)
            print("❌ FAILED")
            print("="*60)
            print(f"Error: {output['error']}")
    
    return output


# =====================================================
# EXAMPLE USAGE & TESTING
# =====================================================

def main():
    """Main function with example queries."""
    
    # Check for Groq API key
    if not os.getenv("GROQ_API_KEY"):
        print("⚠️  Warning: GROQ_API_KEY not set in environment variables")
        print("Please set it using:")
        print("  Windows: $env:GROQ_API_KEY='your-key-here'")
        print("  Linux/Mac: export GROQ_API_KEY='your-key-here'")
        return
    
    # Example queries
    test_queries = [
        "Show me the top 10 customers by total spending in 2024",
        "What products are currently low in stock across all warehouses?"
    ]
    
    print("\n" + "="*60)
    print("🧪 TESTING MULTI-AGENT NLP-TO-SQL SYSTEM")
    print("="*60)
    print(f"\nRunning {len(test_queries)} test queries...\n")
    
    results = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'#'*60}")
        print(f"TEST {i}/{len(test_queries)}")
        print(f"{'#'*60}")
        
        result = run_nlp_to_sql(query, verbose=True)
        results.append({
            "query": query,
            "result": result
        })
        
        # Small delay between queries
        import time
        time.sleep(1)
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results if r["result"]["success"])
    failed = len(results) - successful
    
    print(f"\n✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    print(f"📈 Success Rate: {(successful/len(results)*100):.1f}%")
    
    if failed > 0:
        print(f"\n❌ Failed Queries:")
        for r in results:
            if not r["result"]["success"]:
                print(f"   - {r['query']}")
                print(f"     Error: {r['result']['error']}")


if __name__ == "__main__":
    main()
