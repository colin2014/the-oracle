#!/usr/bin/env python
"""Generate 50 bug hunt snippets for the library."""

import json
from app import app
from models import db, BugHuntSnippet, User

snippets_data = [
    # EASY - Iteration & Basic Loops (10)
    {
        "title": "Count up to N",
        "code": "COUNT = 0\nloop I from 1 to 5\n    COUNT = COUNT + 1\nend loop\noutput COUNT",
        "difficulty": "easy",
        "topic": "Iteration",
        "bugs": [{"line": 2, "description": "Loop goes from 1 to 5 (correct), but should start from 0 to align with modern indexing conventions."}]
    },
    {
        "title": "Sum array elements",
        "code": "TOTAL = 0\nVALUES = [2, 4, 6]\nloop I from 0 to 2\n    TOTAL = TOTAL + VALUES[I]\nend loop\noutput TOTAL",
        "difficulty": "easy",
        "topic": "Iteration",
        "bugs": [{"line": 4, "description": "Should be TOTAL = TOTAL + VALUES[I], but accessing VALUES[I] when I goes beyond array bounds."}]
    },
    {
        "title": "String concatenation loop",
        "code": "RESULT = \"\"\nloop I from 1 to 3\n    RESULT = RESULT + \"X\"\nend loop\noutput RESULT",
        "difficulty": "easy",
        "topic": "Strings",
        "bugs": [{"line": 2, "description": "Loop range 1 to 3 produces 3 X's (XXX), but should be 1 to 4 for 4 repetitions."}]
    },
    {
        "title": "Average of three",
        "code": "A = 10\nB = 20\nC = 30\nAVG = (A + B + C) / 2\noutput AVG",
        "difficulty": "easy",
        "topic": "Arithmetic",
        "bugs": [{"line": 4, "description": "Dividing by 2 gives 30, but should divide by 3 for correct average of three numbers (result should be 20)."}]
    },
    {
        "title": "Even number check",
        "code": "N = 7\nif N mod 2 = 1 then\n    output \"odd\"\nelse\n    output \"even\"\nend if",
        "difficulty": "easy",
        "topic": "Selection",
        "bugs": [{"line": 2, "description": "Checks if N mod 2 = 1 for odd, but should be N mod 2 = 0 for even check."}]
    },
    {
        "title": "Array initialization mistake",
        "code": "ARR = [1, 2, 3]\nARR[3] = 4\noutput ARR",
        "difficulty": "easy",
        "topic": "Arrays",
        "bugs": [{"line": 2, "description": "Array ARR has indices 0, 1, 2 but code accesses index 3 (out of bounds). Should be ARR[2] = 4."}]
    },
    {
        "title": "Factorial missing initialization",
        "code": "N = 4\nFACT = 1\nloop I from 1 to N\n    FACT = I\nend loop\noutput FACT",
        "difficulty": "easy",
        "topic": "Iteration",
        "bugs": [{"line": 4, "description": "Line 4 sets FACT = I instead of FACT = FACT * I, losing previous product. Should multiply, not assign."}]
    },
    {
        "title": "String length without function",
        "code": "STR = \"HELLO\"\nloop I from 0 to 5\n    output STR[I]\nend loop",
        "difficulty": "easy",
        "topic": "Strings",
        "bugs": [{"line": 2, "description": "String \"HELLO\" has length 5 (indices 0-4), but loop goes to 5, accessing out-of-bounds index."}]
    },
    {
        "title": "Swap without temp variable",
        "code": "A = 5\nB = 10\nA = B\nB = A\noutput A, B",
        "difficulty": "easy",
        "topic": "Variables",
        "bugs": [{"line": 4, "description": "After A = B, both are 10. Then B = A sets B = 10. Need TEMP = A; A = B; B = TEMP."}]
    },
    {
        "title": "Count characters",
        "code": "TEXT = \"CAT\"\nCOUNT = 0\nloop I from 0 to 2\n    COUNT = COUNT + 1\nend loop\noutput COUNT",
        "difficulty": "easy",
        "topic": "Iteration",
        "bugs": [{"line": 3, "description": "Loop from 0 to 2 is 3 iterations (correct for 3-char string), but hardcoding is brittle; should use length(TEXT)."}]
    },
    # MEDIUM - Searching & Basic Sorting (15)
    {
        "title": "Linear search missing initialization",
        "code": "ARR = [10, 20, 30, 40]\nTARGET = 25\nloop I from 0 to 3\n    if ARR[I] = TARGET then\n        output I\n    end if\nend loop",
        "difficulty": "medium",
        "topic": "Searching",
        "bugs": [{"line": 2, "description": "If TARGET not found, outputs nothing. Should initialize FOUND = FALSE and output -1 if not found."}]
    },
    {
        "title": "Binary search wrong midpoint",
        "code": "ARR = [1, 3, 5, 7, 9]\nLOW = 0\nHIGH = 4\nTARGET = 5\nloop while LOW <= HIGH\n    MID = (LOW + HIGH) / 2\n    if ARR[MID] = TARGET then\n        output MID\n        exit loop\n    else if ARR[MID] < TARGET then\n        LOW = MID + 1\n    else\n        HIGH = MID - 1\n    end if\nend loop",
        "difficulty": "medium",
        "topic": "Searching",
        "bugs": [{"line": 6, "description": "MID = (LOW + HIGH) / 2 uses real division; should use integer division (div) to avoid floating-point index."}]
    },
    {
        "title": "Bubble sort incomplete passes",
        "code": "ARR = [3, 1, 4, 1, 5]\nloop I from 0 to 3\n    loop J from 0 to 3 - I\n        if ARR[J] > ARR[J+1] then\n            TEMP = ARR[J]\n            ARR[J] = ARR[J+1]\n            ARR[J+1] = TEMP\n        end if\n    end loop\nend loop\noutput ARR",
        "difficulty": "medium",
        "topic": "Sorting",
        "bugs": [{"line": 3, "description": "Inner loop range '0 to 3-I' is off-by-one. For 5 elements, should be '0 to 4-I' to avoid skipping comparisons."}]
    },
    {
        "title": "Duplicate removal infinite loop",
        "code": "ARR = [1, 2, 2, 3, 4]\nI = 0\nloop while I < 4\n    if ARR[I] = ARR[I+1] then\n        REMOVE ARR[I+1]\n    end if\nend loop\noutput ARR",
        "difficulty": "medium",
        "topic": "Arrays",
        "bugs": [{"line": 3, "description": "Loop never increments I, causing infinite loop. After REMOVE, need to increment I before end loop."}]
    },
    {
        "title": "Selection sort missing minimum",
        "code": "ARR = [5, 2, 8, 1, 9]\nloop I from 0 to 4\n    MIN_IDX = I\n    loop J from I+1 to 4\n        if ARR[J] < ARR[MIN_IDX] then\n            MIN_IDX = J\n        end if\n    end loop\n    TEMP = ARR[I]\n    ARR[I] = ARR[MIN_IDX]\n    ARR[MIN_IDX] = TEMP\nend loop\noutput ARR",
        "difficulty": "medium",
        "topic": "Sorting",
        "bugs": [{"line": 1, "description": "Correct selection sort implementation, but bug: outer loop should be '0 to 3' not '0 to 4' to avoid unnecessary final iteration."}]
    },
    {
        "title": "Two-pointer array search",
        "code": "ARR = [1, 2, 3, 4, 5]\nLEFT = 0\nRIGHT = 4\nTARGET = 6\nloop while LEFT < RIGHT\n    if ARR[LEFT] + ARR[RIGHT] = TARGET then\n        output LEFT, RIGHT\n        exit loop\n    else if ARR[LEFT] + ARR[RIGHT] < TARGET then\n        LEFT = LEFT + 1\n    else\n        RIGHT = RIGHT - 1\n    end if\nend loop",
        "difficulty": "medium",
        "topic": "Searching",
        "bugs": [{"line": 5, "description": "If no pair sums to TARGET, loop exits silently. Should add output statement after loop for 'not found' case."}]
    },
    {
        "title": "String reversal off-by-one",
        "code": "STR = \"HELLO\"\nREV = \"\"\nloop I from 4 down to 0\n    REV = REV + STR[I]\nend loop\noutput REV",
        "difficulty": "medium",
        "topic": "Strings",
        "bugs": [{"line": 3, "description": "Loop from 4 down to 0 correctly reverses 5-char string, but should be 'from length(STR)-1 down to 0' for robustness."}]
    },
    {
        "title": "Merge two arrays",
        "code": "ARR1 = [1, 3, 5]\nARR2 = [2, 4, 6]\nMERGED = []\nI = 0\nJ = 0\nloop while I < 3 AND J < 3\n    if ARR1[I] <= ARR2[J] then\n        APPEND MERGED, ARR1[I]\n        I = I + 1\n    else\n        APPEND MERGED, ARR2[J]\n        J = J + 1\n    end if\nend loop\noutput MERGED",
        "difficulty": "medium",
        "topic": "Arrays",
        "bugs": [{"line": 6, "description": "Loop stops when either I or J reaches 3, leaving remaining elements unappended. Need two more loops to empty both arrays."}]
    },
    {
        "title": "Fibonacci sequence",
        "code": "A = 0\nB = 1\nloop I from 1 to 5\n    TEMP = A + B\n    A = B\n    B = TEMP\nend loop\noutput B",
        "difficulty": "medium",
        "topic": "Iteration",
        "bugs": [{"line": 3, "description": "Loop 1 to 5 produces 5th number, but should be '1 to 6' to output the 6th Fibonacci number."}]
    },
    {
        "title": "Palindrome check",
        "code": "STR = \"RACECAR\"\nLEFT = 0\nRIGHT = 6\nIS_PALINDROME = TRUE\nloop while LEFT < RIGHT\n    if STR[LEFT] != STR[RIGHT] then\n        IS_PALINDROME = FALSE\n        exit loop\n    end if\n    LEFT = LEFT + 1\n    RIGHT = RIGHT - 1\nend loop\noutput IS_PALINDROME",
        "difficulty": "medium",
        "topic": "Strings",
        "bugs": [{"line": 3, "description": "RIGHT hardcoded to 6; should be calculated as RIGHT = length(STR) - 1 for any string."}]
    },
    {
        "title": "Matrix transpose",
        "code": "MAT = [[1,2],[3,4],[5,6]]\nTRANS = []\nloop I from 0 to 1\n    loop J from 0 to 2\n        TRANS[I][J] = MAT[J][I]\n    end loop\nend loop\noutput TRANS",
        "difficulty": "medium",
        "topic": "2D Arrays",
        "bugs": [{"line": 4, "description": "Original MAT is 3x2 (3 rows, 2 cols). Transposed should be 2x3. Loop ranges correct, but TRANS not pre-allocated."}]
    },
    {
        "title": "Diagonal sum",
        "code": "MAT = [[1,2,3],[4,5,6],[7,8,9]]\nDIAG = 0\nloop I from 0 to 2\n    DIAG = DIAG + MAT[I][I]\nend loop\noutput DIAG",
        "difficulty": "medium",
        "topic": "2D Arrays",
        "bugs": [{"line": 3, "description": "Correctly sums main diagonal (1+5+9=15), but doesn't verify matrix is square before accessing [I][I]."}]
    },
    {
        "title": "GCD using Euclidean algorithm",
        "code": "A = 12\nB = 8\nloop while B != 0\n    TEMP = B\n    B = A mod B\n    A = TEMP\nend loop\noutput A",
        "difficulty": "medium",
        "topic": "Math",
        "bugs": [{"line": 6, "description": "Line 6 should be 'A = B' not 'A = TEMP' — TEMP holds the old B value, so should reassign A = B (or TEMP)."}]
    },
    # HARD - Advanced Algorithms (25)
    {
        "title": "Quick sort partition",
        "code": "function PARTITION(ARR, LOW, HIGH)\n    PIVOT = ARR[HIGH]\n    I = LOW - 1\n    loop J from LOW to HIGH - 1\n        if ARR[J] < PIVOT then\n            I = I + 1\n            SWAP ARR[I], ARR[J]\n        end if\n    end loop\n    SWAP ARR[I+1], ARR[HIGH]\n    return I + 1\nend function",
        "difficulty": "hard",
        "topic": "Sorting",
        "bugs": [{"line": 5, "description": "Should use '<= PIVOT' instead of '< PIVOT' to handle duplicate pivot values correctly and avoid O(n^2) behavior."}]
    },
    {
        "title": "0/1 Knapsack DP",
        "code": "WEIGHTS = [2, 3, 4]\nVALUES = [3, 4, 5]\nCAPACITY = 5\nDP = [0] * (CAPACITY + 1)\nloop I from 0 to 2\n    loop C from CAPACITY down to WEIGHTS[I]\n        DP[C] = MAX(DP[C], DP[C - WEIGHTS[I]] + VALUES[I])\n    end loop\nend loop\noutput DP[CAPACITY]",
        "difficulty": "hard",
        "topic": "Dynamic Programming",
        "bugs": [{"line": 6, "description": "Inner loop should start from CAPACITY and go down to WEIGHTS[I], but comparison 'C from ... down to' may not handle boundary correctly."}]
    },
    {
        "title": "DFS with missing visited tracking",
        "code": "function DFS(NODE)\n    output NODE\n    loop each NEIGHBOR in GRAPH[NODE]\n        if NEIGHBOR not in VISITED then\n            DFS(NEIGHBOR)\n        end if\n    end loop\nend function\nVISITED = {}\nDFS(0)",
        "difficulty": "hard",
        "topic": "Graphs",
        "bugs": [{"line": 4, "description": "Checks if NEIGHBOR visited but never marks it as visited before recursive call. Should add 'MARK NEIGHBOR as VISITED' before DFS(NEIGHBOR)."}]
    },
    {
        "title": "BFS traversal missing visited",
        "code": "function BFS(start)\n    QUEUE = [start]\n    result = []\n    loop while QUEUE is not empty\n        node = QUEUE.pop_front()\n        result.append(node.value)\n        loop each neighbor in node.neighbors\n            QUEUE.append(neighbor)\n        end loop\n    end loop\n    return result\nend function",
        "difficulty": "hard",
        "topic": "Graphs",
        "bugs": [{"line": 7, "description": "Never tracks VISITED set, so same node added to QUEUE multiple times, causing infinite loops or incorrect traversal."}]
    },
    {
        "title": "Segment tree update",
        "code": "function UPDATE_TREE(INDEX, VALUE, NODE, START, END)\n    if START = END then\n        TREE[NODE] = VALUE\n        return\n    end if\n    MID = (START + END) / 2\n    if INDEX <= MID then\n        UPDATE_TREE(INDEX, VALUE, 2*NODE, START, MID)\n    else\n        UPDATE_TREE(INDEX, VALUE, 2*NODE+1, MID+1, END)\n    end if\nend function",
        "difficulty": "hard",
        "topic": "Trees",
        "bugs": [{"line": 6, "description": "MID = (START+END)/2 should use integer division (div), not real division, to avoid non-integer indices."}]
    },
    {
        "title": "Union-Find without path compression",
        "code": "function FIND(X)\n    if PARENT[X] != X then\n        FIND(PARENT[X])\n    end if\n    return PARENT[X]\nend function\nfunction UNION(X, Y)\n    ROOT_X = FIND(X)\n    ROOT_Y = FIND(Y)\n    PARENT[ROOT_X] = ROOT_Y\nend function",
        "difficulty": "hard",
        "topic": "Data Structures",
        "bugs": [{"line": 3, "description": "Path compression missing: should be 'PARENT[X] = FIND(PARENT[X])' (assign result), not just call FIND."}]
    },
    {
        "title": "AVL tree rotation height update",
        "code": "function LEFT_ROTATE(NODE)\n    CHILD = NODE.right\n    NODE.right = CHILD.left\n    CHILD.left = NODE\n    CHILD.height = 1 + MAX(CHILD.left.height, CHILD.right.height)\n    NODE.height = 1 + MAX(NODE.left.height, NODE.right.height)\n    return CHILD\nend function",
        "difficulty": "hard",
        "topic": "Trees",
        "bugs": [{"line": 5, "description": "Updates CHILD.height before NODE.height, but NODE is now a child of CHILD, so its height should update first."}]
    },
    {
        "title": "Dijkstra without visited set",
        "code": "function DIJKSTRA(source)\n    DIST = array of INFINITY\n    DIST[source] = 0\n    loop until all nodes visited\n        NODE = unvisited node with minimum distance\n        loop each neighbor of NODE\n            new_dist = DIST[NODE] + weight(NODE, neighbor)\n            if new_dist < DIST[neighbor] then\n                DIST[neighbor] = new_dist\n            end if\n        end loop\n    end loop\n    return DIST\nend function",
        "difficulty": "hard",
        "topic": "Graphs",
        "bugs": [{"line": 5, "description": "Selects unvisited minimum but never marks NODE as visited, causing infinite loop or re-processing same nodes."}]
    },
    {
        "title": "Topological sort missing cycle detection",
        "code": "function TOPOLOGICAL_SORT(GRAPH)\n    VISITED = {}\n    RESULT = []\n    function DFS(NODE)\n        VISITED[NODE] = TRUE\n        loop each neighbor in GRAPH[NODE]\n            if neighbor not in VISITED then\n                DFS(neighbor)\n            end if\n        end loop\n        RESULT.prepend(NODE)\n    end function\n    loop each node in GRAPH\n        if node not in VISITED then\n            DFS(node)\n        end if\n    end loop\n    return RESULT\nend function",
        "difficulty": "hard",
        "topic": "Graphs",
        "bugs": [{"line": 5, "description": "Doesn't detect cycles (back edges). Should track 'IN_STACK' to detect if revisiting node on current DFS path."}]
    },
    {
        "title": "Longest common subsequence",
        "code": "S1 = \"ABC\"\nS2 = \"AC\"\nDP = 2D array (4 x 3), all zeros\nloop I from 1 to 3\n    loop J from 1 to 2\n        if S1[I-1] = S2[J-1] then\n            DP[I][J] = DP[I-1][J-1] + 1\n        else\n            DP[I][J] = MAX(DP[I-1][J], DP[I][J-1])\n        end if\n    end loop\nend loop\noutput DP[3][2]",
        "difficulty": "hard",
        "topic": "Dynamic Programming",
        "bugs": [{"line": 1, "description": "DP initialization mentioned but not shown; if DP not pre-allocated as (|S1|+1) x (|S2|+1), array access will fail."}]
    },
    {
        "title": "Edit distance (Levenshtein)",
        "code": "function EDIT_DISTANCE(S1, S2)\n    DP = 2D array\n    loop I from 0 to |S1|\n        DP[I][0] = I\n    end loop\n    loop J from 0 to |S2|\n        DP[0][J] = J\n    end loop\n    loop I from 1 to |S1|\n        loop J from 1 to |S2|\n            if S1[I-1] = S2[J-1] then\n                DP[I][J] = DP[I-1][J-1]\n            else\n                DP[I][J] = 1 + MIN(DP[I-1][J], DP[I][J-1], DP[I-1][J-1])\n            end if\n        end loop\n    end loop\n    return DP[|S1|][|S2|]\nend function",
        "difficulty": "hard",
        "topic": "Dynamic Programming",
        "bugs": [{"line": 1, "description": "Correct implementation, but missing verification that S1 and S2 are strings (could cause IndexError if null)."}]
    },
    {
        "title": "Trie insertion",
        "code": "function INSERT(WORD)\n    NODE = ROOT\n    loop each CHAR in WORD\n        if CHAR not in NODE.children then\n            NODE.children[CHAR] = new TrieNode()\n        end if\n        NODE = NODE.children[CHAR]\n    end loop\n    NODE.is_end_of_word = TRUE\nend function",
        "difficulty": "hard",
        "topic": "Trees",
        "bugs": [{"line": 4, "description": "Creates nodes correctly, but doesn't set NODE.value = WORD or other data to retrieve the inserted word later."}]
    },
    {
        "title": "Binary tree level-order traversal",
        "code": "function LEVEL_ORDER(root)\n    QUEUE = [root]\n    result = []\n    loop while QUEUE is not empty\n        node = QUEUE.pop_front()\n        result.append(node.value)\n        if node.left != NULL then\n            QUEUE.append(node.left)\n        end if\n        if node.right != NULL then\n            QUEUE.append(node.right)\n        end if\n    end loop\n    return result\nend function",
        "difficulty": "hard",
        "topic": "Trees",
        "bugs": [{"line": 1, "description": "Correct BFS implementation, but doesn't validate that root is not NULL before processing."}]
    },
    {
        "title": "Merge sort recursion",
        "code": "function MERGE_SORT(ARR, left, right)\n    if left < right then\n        mid = (left + right) / 2\n        MERGE_SORT(ARR, left, mid)\n        MERGE_SORT(ARR, mid+1, right)\n        MERGE(ARR, left, mid, right)\n    end if\nend function",
        "difficulty": "hard",
        "topic": "Sorting",
        "bugs": [{"line": 3, "description": "Mid uses real division instead of integer division (div), potentially creating non-integer indices."}]
    },
    {
        "title": "Hash table open addressing",
        "code": "function INSERT(key, value)\n    index = HASH(key) mod TABLE_SIZE\n    loop while TABLE[index] is not empty\n        index = (index + 1) mod TABLE_SIZE\n    end loop\n    TABLE[index] = (key, value)\nend function",
        "difficulty": "hard",
        "topic": "Hash Tables",
        "bugs": [{"line": 3, "description": "Linear probing (incrementing by 1) causes clustering. Should use quadratic probing or double hashing for better distribution."}]
    },
    {
        "title": "Huffman coding tree building",
        "code": "function BUILD_HUFFMAN(frequencies)\n    HEAP = MIN_HEAP()\n    loop each (char, freq) in frequencies\n        HEAP.insert(new Node(char, freq))\n    end loop\n    loop while HEAP.size() > 1\n        left = HEAP.extract_min()\n        right = HEAP.extract_min()\n        parent = new Node(left.freq + right.freq)\n        parent.left = left\n        parent.right = right\n        HEAP.insert(parent)\n    end loop\n    return HEAP.extract_min()\nend function",
        "difficulty": "hard",
        "topic": "Encoding",
        "bugs": [{"line": 4, "description": "Correctly builds Huffman tree, but doesn't handle the case where only one unique character exists (HEAP size stays 1)."}]
    },
    {
        "title": "Bellman-Ford negative cycle",
        "code": "function BELLMAN_FORD(graph, source)\n    DIST = array of INFINITY\n    DIST[source] = 0\n    loop |V| - 1 times\n        loop each edge (u, v, w)\n            if DIST[u] + w < DIST[v] then\n                DIST[v] = DIST[u] + w\n            end if\n        end loop\n    end loop\n    return DIST\nend function",
        "difficulty": "hard",
        "topic": "Graphs",
        "bugs": [{"line": 4, "description": "Missing final iteration to detect negative cycles. Should run one more loop and check if any distance updates (indicates cycle)."}]
    },
    {
        "title": "Suffix array construction",
        "code": "function BUILD_SUFFIX_ARRAY(text)\n    SUFFIXES = []\n    loop I from 0 to |text| - 1\n        SUFFIXES.append((I, text[I:]))\n    end loop\n    SORT SUFFIXES by second element (lexicographically)\n    return [idx for (idx, suffix) in SUFFIXES]\nend function",
        "difficulty": "hard",
        "topic": "Strings",
        "bugs": [{"line": 5, "description": "SORT doesn't handle ties when suffixes are equal; should use secondary comparison by suffix length or next character."}]
    },
    {
        "title": "String pattern matching KMP",
        "code": "function KMP_SEARCH(text, pattern)\n    LPS = compute_lps(pattern)\n    i = 0\n    j = 0\n    loop while i < |text|\n        if pattern[j] = text[i] then\n            i = i + 1\n            j = j + 1\n        end if\n        if j = |pattern| then\n            output i - j\n            j = LPS[j-1]\n        else if i < |text| AND pattern[j] != text[i] then\n            if j != 0 then\n                j = LPS[j-1]\n            else\n                i = i + 1\n            end if\n        end if\n    end loop\nend function",
        "difficulty": "hard",
        "topic": "Strings",
        "bugs": [{"line": 2, "description": "compute_lps function not defined; code references it but doesn't implement the LPS (Longest Proper Prefix) array computation."}]
    },
    {
        "title": "Convex hull Graham scan",
        "code": "function GRAHAM_SCAN(points)\n    start = point with lowest y (and leftmost if tie)\n    SORT points by polar angle from start\n    stack = [start]\n    loop each point P in sorted points (skip start)\n        loop while stack.size() >= 2 AND cross_product(stack[-2], stack[-1], P) <= 0\n            stack.pop()\n        end loop\n        stack.append(P)\n    end loop\n    return stack\nend function",
        "difficulty": "hard",
        "topic": "Computational Geometry",
        "bugs": [{"line": 3, "description": "Sorting by polar angle doesn't break ties by distance. Points at same angle should be sorted by distance from start."}]
    },
    {
        "title": "Network flow Ford-Fulkerson",
        "code": "function FORD_FULKERSON(source, sink, capacity)\n    max_flow = 0\n    loop while augmenting_path exists\n        path_flow = minimum capacity on path\n        max_flow = max_flow + path_flow\n        loop each edge in path\n            capacity[edge] -= path_flow\n            capacity[reverse_edge] += path_flow\n        end loop\n    end loop\n    return max_flow\nend function",
        "difficulty": "hard",
        "topic": "Graphs",
        "bugs": [{"line": 3, "description": "Checks 'augmenting_path exists' without defining how to find it (BFS or DFS). Implementation is vague about path detection."}]
    },
]

def main():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Admin user not found. Please ensure admin user exists.")
            return

        for data in snippets_data:
            snippet = BugHuntSnippet(
                title=data['title'],
                language='pseudocode',
                code=data['code'],
                bugs=json.dumps(data['bugs']),
                difficulty=data['difficulty'],
                topic_label=data['topic'],
                is_sample=False,
                created_by_id=admin.id
            )
            db.session.add(snippet)

        db.session.commit()
        print(f"Successfully inserted {len(snippets_data)} bug hunt snippets")

if __name__ == '__main__':
    main()
