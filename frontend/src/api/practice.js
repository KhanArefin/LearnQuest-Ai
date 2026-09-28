/**
 * Practice Problems & Skill Verification API.
 * OWNER: Member 2 (Learning Management).
 *
 * Contract:
 * - GET  /api/practice/problems             -> list of problems with tags, difficulty, status
 * - GET  /api/practice/problems/{id}        -> full problem specification with test cases
 * - POST /api/practice/problems/{id}/submit -> run test cases & return pass/fail per case
 * - GET  /api/practice/skills               -> verification status per skill (e.g., N passed)
 *
 * Note: If backend practice endpoints are pending from team integration,
 * DEV_FALLBACK_PROBLEMS serves as an isolated, removable development fallback.
 */

import client from './client';

// ============================================================================
// ISOLATED DEV FALLBACK DATA (Removable once backend practice router lands)
// ============================================================================
const DEV_FALLBACK_SKILLS = [
  {
    id: 'dbms.sql_joins',
    name: 'SQL Joins & Grouping',
    required_to_verify: 2,
    passed_count: 2,
    verified: true,
  },
  {
    id: 'dbms.relational_algebra',
    name: 'Relational Algebra',
    required_to_verify: 2,
    passed_count: 1,
    verified: false,
  },
  {
    id: 'dbms.indexing',
    name: 'Indexing & Query Plans',
    required_to_verify: 2,
    passed_count: 0,
    verified: false,
  },
];

const DEV_FALLBACK_PROBLEMS = [
  {
    id: 'prob-sql-01',
    title: 'Customer Order Aggregate Summary',
    slug: 'customer-order-aggregate-summary',
    skill_id: 'dbms.sql_joins',
    skill_name: 'SQL Joins & Grouping',
    difficulty: 'easy',
    topic_tag: 'dbms.sql_joins',
    acceptance_rate: '84.2%',
    total_submissions: 1420,
    status: 'solved', // 'solved' | 'attempted' | 'unsolved'
    statement_md: `Given two tables, \`customers\` and \`orders\`, write a SQL query to return each customer's \`customer_id\`, \`name\`, and the total dollar amount spent across all completed orders.
    
If a customer has no orders, their total spent should be displayed as \`0\`.
Sort the result in descending order of total spent, then ascending order of \`customer_id\`.`,
    input_format: `Two tables in standard relational format:
- \`customers(customer_id INT, name VARCHAR(100))\`
- \`orders(order_id INT, customer_id INT, amount DECIMAL(10,2), status VARCHAR(20))\``,
    output_format: `Result set with columns: \`customer_id\`, \`name\`, \`total_spent\``,
    constraints: [
      '1 <= number of customers <= 10,000',
      '0 <= number of orders per customer <= 500',
      'Amounts are non-negative decimal numbers with 2 decimal places',
    ],
    examples: [
      {
        input: `customers:
1 | Alice
2 | Bob
3 | Charlie

orders:
101 | 1 | 50.00 | completed
102 | 1 | 30.00 | completed
103 | 2 | 20.00 | cancelled`,
        output: `1 | Alice | 80.00
2 | Bob   | 0.00
3 | Charlie | 0.00`,
        explanation: 'Bob has an order, but it was cancelled. Charlie has no orders at all. Both show 0.00 total spent.',
      },
    ],
    starter_code: `-- Write your SQL query below:
SELECT
    c.customer_id,
    c.name,
    COALESCE(SUM(CASE WHEN o.status = 'completed' THEN o.amount ELSE 0 END), 0) AS total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC, c.customer_id ASC;`,
    test_cases: [
      {
        id: 'tc-1',
        title: 'Basic completed orders and non-ordering customer',
        is_hidden: false,
        input_preview: '3 customers, 4 orders (1 cancelled)',
        expected_output: '1 | Alice | 80.00\n2 | Bob | 0.00\n3 | Charlie | 0.00',
      },
      {
        id: 'tc-2',
        title: 'Tie-breaker customer_id ordering test',
        is_hidden: false,
        input_preview: '5 customers with identical spending',
        expected_output: '10 | Dave | 50.00\n11 | Eve | 50.00\n12 | Frank | 50.00',
      },
      {
        id: 'tc-3',
        title: 'Scale & NULL edge cases',
        is_hidden: true,
        input_preview: 'Hidden performance dataset (500 rows)',
        expected_output: 'Passed on hidden test harness',
      },
    ],
  },
  {
    id: 'prob-sql-02',
    title: 'Self-Join Department Manager Hierarchy',
    slug: 'self-join-department-manager-hierarchy',
    skill_id: 'dbms.sql_joins',
    skill_name: 'SQL Joins & Grouping',
    difficulty: 'medium',
    topic_tag: 'dbms.sql_joins',
    acceptance_rate: '68.5%',
    total_submissions: 980,
    status: 'solved',
    statement_md: `Write a query to find all employees whose salary is greater than their direct manager's salary.
    
Return employee name, employee salary, manager name, and manager salary.`,
    input_format: `Table: \`employees(id INT, name VARCHAR(100), salary INT, manager_id INT)\``,
    output_format: `Columns: \`employee_name\`, \`employee_salary\`, \`manager_name\`, \`manager_salary\``,
    constraints: ['Every employee has at most one direct manager', 'Root managers have manager_id IS NULL'],
    examples: [
      {
        input: `id | name | salary | manager_id
1  | Joe  | 70000  | 3
2  | Henry| 80000  | 4
3  | Sam  | 60000  | NULL
4  | Max  | 90000  | NULL`,
        output: `Joe | 70000 | Sam | 60000`,
        explanation: 'Joe earns 70,000 which exceeds Sam\'s salary of 60,000.',
      },
    ],
    starter_code: `SELECT
    e.name AS employee_name,
    e.salary AS employee_salary,
    m.name AS manager_name,
    m.salary AS manager_salary
FROM employees e
JOIN employees m ON e.manager_id = m.id
WHERE e.salary > m.salary;`,
    test_cases: [
      {
        id: 'tc-1',
        title: 'Direct salary comparison',
        is_hidden: false,
        input_preview: '4 employees, 2 managers',
        expected_output: 'Joe | 70000 | Sam | 60000',
      },
      {
        id: 'tc-2',
        title: 'All employees earn less than manager',
        is_hidden: false,
        input_preview: 'Strict hierarchical pyramid',
        expected_output: '(0 rows returned)',
      },
    ],
  },
  {
    id: 'prob-relalg-01',
    title: 'Duplicate Tuple Elimination in Set Projection',
    slug: 'duplicate-tuple-elimination-set-projection',
    skill_id: 'dbms.relational_algebra',
    skill_name: 'Relational Algebra',
    difficulty: 'easy',
    topic_tag: 'dbms.relational_algebra',
    acceptance_rate: '91.0%',
    total_submissions: 2150,
    status: 'solved',
    statement_md: `In mathematical relational algebra, relations are defined as sets rather than multisets (bags).
    
Given an input table containing duplicate rows along non-key attributes, write an expression or query that projects columns \`(department, role)\` ensuring duplicate tuples are strictly eliminated as required by set theory.`,
    input_format: `Table: \`staff(staff_id INT, department VARCHAR(50), role VARCHAR(50))\``,
    output_format: `Unique set of \`(department, role)\` pairs`,
    constraints: ['Standard relational algebra semantics apply'],
    examples: [
      {
        input: `1 | Engineering | Developer\n2 | Engineering | Developer\n3 | Design | Lead`,
        output: `Design | Lead\nEngineering | Developer`,
        explanation: 'Duplicate Developer row is eliminated by projection π.',
      },
    ],
    starter_code: `SELECT DISTINCT department, role
FROM staff
ORDER BY department, role;`,
    test_cases: [
      {
        id: 'tc-1',
        title: 'Duplicate projection elimination',
        is_hidden: false,
        input_preview: '3 staff members with 2 duplicates',
        expected_output: 'Design | Lead\nEngineering | Developer',
      },
    ],
  },
  {
    id: 'prob-relalg-02',
    title: 'Division Operator Simulation via Difference',
    slug: 'division-operator-simulation-via-difference',
    skill_id: 'dbms.relational_algebra',
    skill_name: 'Relational Algebra',
    difficulty: 'hard',
    topic_tag: 'dbms.relational_algebra',
    acceptance_rate: '45.1%',
    total_submissions: 512,
    status: 'unsolved',
    statement_md: `Relational division (R ÷ S) finds tuples in R that are associated with *all* tuples in S.
    
Given table \`student_skills(student_id, skill)\` and table \`required_skills(skill)\`, find all students who possess every skill in \`required_skills\`. Express this without relying on non-relational procedural loops.`,
    input_format: `Tables: \`student_skills(student_id INT, skill VARCHAR(50))\`, \`required_skills(skill VARCHAR(50))\``,
    output_format: `List of qualifying \`student_id\` values`,
    constraints: ['Must produce correct result when required_skills contains 1 to 20 skills'],
    examples: [
      {
        input: `student_skills:
1 | SQL
1 | Python
2 | SQL

required_skills:
SQL
Python`,
        output: `1`,
        explanation: 'Only student 1 possesses both SQL and Python.',
      },
    ],
    starter_code: `SELECT s.student_id
FROM student_skills s
JOIN required_skills r ON s.skill = r.skill
GROUP BY s.student_id
HAVING COUNT(DISTINCT s.skill) = (SELECT COUNT(*) FROM required_skills);`,
    test_cases: [
      {
        id: 'tc-1',
        title: 'Full match requirement',
        is_hidden: false,
        input_preview: 'Students with subset vs exact vs superset skills',
        expected_output: '1',
      },
      {
        id: 'tc-2',
        title: 'No matching students',
        is_hidden: false,
        input_preview: 'Disjoint skill sets',
        expected_output: '(Empty set)',
      },
    ],
  },
  {
    id: 'prob-idx-01',
    title: 'B-Tree Composite Index Column Ordering',
    slug: 'b-tree-composite-index-column-ordering',
    skill_id: 'dbms.indexing',
    skill_name: 'Indexing & Query Plans',
    difficulty: 'medium',
    topic_tag: 'dbms.indexing',
    acceptance_rate: '62.0%',
    total_submissions: 740,
    status: 'unsolved',
    statement_md: `A database table \`events(user_id, status, created_at)\` executes frequent queries of the pattern:
\`\`\`sql
SELECT * FROM events
WHERE user_id = ? AND status = 'active'
ORDER BY created_at DESC
LIMIT 10;
\`\`\`
Determine and create the optimal composite B-Tree index to satisfy both the equality filters and the range/sort order without requiring an explicit in-memory filesort.`,
    input_format: `Table \`events\` with 5,000,000 rows`,
    output_format: `DDL statement creating the index`,
    constraints: ['Index must avoid external sort on created_at'],
    examples: [
      {
        input: `Equality: user_id, status; Sort: created_at DESC`,
        output: `CREATE INDEX idx_events_perf ON events (user_id, status, created_at DESC);`,
        explanation: 'Leading columns satisfy equality, trailing column satisfies sort.',
      },
    ],
    starter_code: `CREATE INDEX idx_events_composite ON events (user_id, status, created_at DESC);`,
    test_cases: [
      {
        id: 'tc-1',
        title: 'Filter + Sort index layout check',
        is_hidden: false,
        input_preview: 'Query execution plan EXPLAIN validation',
        expected_output: 'Index Scan without Using filesort',
      },
    ],
  },
];

// In-memory session tracking for demo / dev attempts
const localAttempts = {};

// ============================================================================
// API METHODS (Tries real backend first, falls back gracefully)
// ============================================================================

export const listProblems = async (params = {}) => {
  try {
    const res = await client.get('/api/practice/problems', { params });
    return res?.data || res;
  } catch (err) {
    // Isolated fallback if backend router is not yet registered
    if (err?.response?.status === 404 || err?.status === 404 || err?.code === 'ERR_BAD_RESPONSE') {
      let filtered = [...DEV_FALLBACK_PROBLEMS];
      if (params.skill) {
        filtered = filtered.filter((p) => p.skill_id === params.skill || p.topic_tag === params.skill);
      }
      if (params.difficulty) {
        filtered = filtered.filter((p) => p.difficulty === params.difficulty);
      }
      if (params.search) {
        const q = params.search.toLowerCase();
        filtered = filtered.filter(
          (p) => p.title.toLowerCase().includes(q) || p.statement_md.toLowerCase().includes(q)
        );
      }
      return { items: filtered, total: filtered.length };
    }
    throw err;
  }
};

export const getProblem = async (problemId) => {
  try {
    const res = await client.get(`/api/practice/problems/${problemId}`);
    return res?.data || res;
  } catch (err) {
    if (err?.response?.status === 404 || err?.status === 404) {
      const prob = DEV_FALLBACK_PROBLEMS.find(
        (p) => p.id === problemId || p.slug === problemId
      );
      if (prob) return prob;
    }
    throw err;
  }
};

export const submitProblem = async (problemId, { code }) => {
  try {
    const res = await client.post(`/api/practice/problems/${problemId}/submit`, { code });
    return res?.data || res;
  } catch (err) {
    if (err?.response?.status === 404 || err?.status === 404) {
      // Contract-compatible simulated run for development testing
      const prob = DEV_FALLBACK_PROBLEMS.find((p) => p.id === problemId || p.slug === problemId);
      const isBlank = !code || code.trim().length === 0;

      const caseResults = (prob?.test_cases || []).map((tc, index) => {
        const passed = !isBlank && code.length > 15;
        return {
          test_case_id: tc.id,
          title: tc.title,
          is_hidden: tc.is_hidden,
          status: passed ? 'passed' : 'failed',
          actual_output: passed ? tc.expected_output : '(Incorrect result or syntax error)',
          expected_output: tc.is_hidden ? '(Hidden)' : tc.expected_output,
          execution_ms: Math.floor(Math.random() * 25) + 8,
        };
      });

      const allPassed = caseResults.every((c) => c.status === 'passed');
      const passedCount = caseResults.filter((c) => c.status === 'passed').length;

      const attemptRecord = {
        attempt_id: `att-${Date.now()}`,
        problem_id: problemId,
        submitted_at: new Date().toISOString(),
        all_passed: allPassed,
        passed_test_cases: passedCount,
        total_test_cases: caseResults.length,
        test_case_results: caseResults,
        skill_verified: allPassed && prob?.skill_id === 'dbms.sql_joins',
      };

      if (!localAttempts[problemId]) localAttempts[problemId] = [];
      localAttempts[problemId].unshift(attemptRecord);

      return attemptRecord;
    }
    throw err;
  }
};

export const getSkillStatus = async () => {
  try {
    const res = await client.get('/api/practice/skills');
    return res?.data || res;
  } catch (err) {
    if (err?.response?.status === 404 || err?.status === 404) {
      return { items: DEV_FALLBACK_SKILLS };
    }
    throw err;
  }
};
