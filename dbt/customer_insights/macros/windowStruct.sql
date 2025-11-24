{% macro window_struct_call(col) %}
CASE
  WHEN {{ col }} >= 6  AND {{ col }} < 9  THEN '6-9 am'
  WHEN {{ col }} >= 9  AND {{ col }} < 12 THEN '9-12 pm'
  WHEN {{ col }} >= 12 AND {{ col }} < 15 THEN '12-3 pm'
  WHEN {{ col }} >= 15 AND {{ col }} < 18 THEN '3-6 pm'
  WHEN {{ col }} >= 18 AND {{ col }} < 21 THEN '6-9 pm'
  WHEN {{ col }} >= 21 AND {{ col }} < 24 THEN '9-12 am'
END
{% endmacro %}
