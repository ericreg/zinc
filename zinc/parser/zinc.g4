grammar zinc;

// ============================================================================
// Parser Rules
// ============================================================================

program
    : statement* EOF
    ;

statement
    : useStatement
    | structDeclaration
    | functionDeclaration
    | asyncFunctionDeclaration
    | variableAssignment
    | expressionStatement
    | ifStatement
    | forStatement
    | whileStatement
    | loopStatement
    | matchStatement
    | returnStatement
    | breakStatement
    | continueStatement
    | spawnStatement
    | block
    ;

// --- Use/Import Statement ---
useStatement
    : 'use' modulePath ';'
    ;

modulePath
    : IDENTIFIER ('::' IDENTIFIER)*
    ;

// --- Struct Declaration ---
structDeclaration
    : 'struct' IDENTIFIER '{' structBody '}'
    ;

structBody
    : structMember (',' structMember)* ','?
    ;

structMember
    : IDENTIFIER                    // field
    | functionDeclaration           // method
    ;

// --- Function Declaration ---
functionDeclaration
    : 'fn' IDENTIFIER '(' parameterList? ')' block
    ;

asyncFunctionDeclaration
    : 'async' IDENTIFIER '(' parameterList? ')' block
    ;

parameterList
    : parameter (',' parameter)*
    ;

parameter
    : IDENTIFIER (':' type)?
    ;

type
    : IDENTIFIER ('<' typeList '>')?
    | '[' type ']'                  // array type
    | '(' typeList? ')' '->' type   // function type
    ;

typeList
    : type (',' type)*
    ;

// --- Statements ---
variableAssignment
    : assignmentTarget '=' expression
    ;

assignmentTarget
    : IDENTIFIER
    | memberAccess
    | indexAccess
    ;

expressionStatement
    : expression
    ;

ifStatement
    : 'if' expression block ('else' 'if' expression block)* ('else' block)?
    ;

forStatement
    : 'for' IDENTIFIER 'in' expression block
    ;

whileStatement
    : 'while' expression block
    ;

loopStatement
    : 'loop' block
    ;

matchStatement
    : 'match' expression '{' matchArm (',' matchArm)* ','? '}'
    ;

matchArm
    : pattern '=>' (block | expression)
    ;

pattern
    : '_'                                       // wildcard
    | literal                                   // literal pattern
    | IDENTIFIER                                // binding pattern
    | rangePattern                              // range pattern (e.g., 0..17)
    | '(' pattern (',' pattern)* ')'            // tuple pattern
    | IDENTIFIER '{' fieldPattern (',' fieldPattern)* ','? '}'  // struct pattern
    ;

rangePattern
    : INTEGER '..' INTEGER
    | INTEGER '..=' INTEGER
    ;

fieldPattern
    : IDENTIFIER (':' pattern)?
    ;

returnStatement
    : 'return' expression?
    ;

breakStatement
    : 'break'
    ;

continueStatement
    : 'continue'
    ;

spawnStatement
    : 'spawn' expression '(' argumentList? ')'
    ;

block
    : '{' statement* '}'
    ;

// --- Expressions ---
expression
    : primaryExpression                                         # primaryExpr
    | expression '.' IDENTIFIER                                 # memberAccessExpr
    | expression '[' expression ']'                             # indexAccessExpr
    | expression '(' argumentList? ')'                          # functionCallExpr
    | 'await' expression                                        # awaitExpr
    | ('!' | '-' | 'not') expression                            # unaryExpr
    | expression ('*' | '/' | '%') expression                   # multiplicativeExpr
    | expression ('+' | '-') expression                         # additiveExpr
    | expression ('..' | '..=') expression                      # rangeExpr
    | expression ('<' | '<=' | '>' | '>=') expression           # relationalExpr
    | expression ('==' | '!=') expression                       # equalityExpr
    | expression ('and' | '&&') expression                      # logicalAndExpr
    | expression ('or' | '||') expression                       # logicalOrExpr
    | selectExpression                                          # selectExpr
    | lambdaExpression                                          # lambdaExpr
    | '(' expression ')'                                        # parenExpr
    ;

primaryExpression
    : literal
    | IDENTIFIER
    | arrayLiteral
    | structInstantiation
    ;

memberAccess
    : expression '.' IDENTIFIER
    ;

indexAccess
    : expression '[' expression ']'
    ;

literal
    : INTEGER
    | FLOAT
    | STRING
    | booleanLiteral
    | 'nil'
    ;

booleanLiteral
    : 'true'
    | 'false'
    ;

arrayLiteral
    : '[' (expression (',' expression)* ','?)? ']'
    ;

structInstantiation
    : IDENTIFIER '{' (fieldInit (',' fieldInit)* ','?)? '}'
    ;

fieldInit
    : IDENTIFIER '=' expression
    ;

argumentList
    : expression (',' expression)*
    ;

selectExpression
    : 'select' '{' selectCase+ '}'
    ;

selectCase
    : 'case' 'await' expression block
    | 'case' expression block
    ;

lambdaExpression
    : '|' parameterList? '|' (expression | block)
    ;

// ============================================================================
// Lexer Rules
// ============================================================================

// --- Keywords ---
USE         : 'use';
STRUCT      : 'struct';
FN          : 'fn';
ASYNC       : 'async';
AWAIT       : 'await';
IF          : 'if';
ELSE        : 'else';
FOR         : 'for';
IN          : 'in';
WHILE       : 'while';
LOOP        : 'loop';
MATCH       : 'match';
RETURN      : 'return';
BREAK       : 'break';
CONTINUE    : 'continue';
TRUE        : 'true';
FALSE       : 'false';
NIL         : 'nil';
AND         : 'and';
OR          : 'or';
NOT         : 'not';
SELF        : 'self';
SELECT      : 'select';
CASE        : 'case';
SPAWN       : 'spawn';

// --- Literals ---
INTEGER
    : '0'
    | [1-9] [0-9]*
    | '0x' [0-9a-fA-F]+
    | '0o' [0-7]+
    | '0b' [01]+
    ;

FLOAT
    : [0-9]+ '.' [0-9]+ ([eE] [+-]? [0-9]+)?
    | [0-9]+ [eE] [+-]? [0-9]+
    ;

STRING
    : '"' (~["\\\r\n] | EscapeSequence)* '"'
    | '\'' (~['\\\r\n] | EscapeSequence)* '\''
    ;

fragment EscapeSequence
    : '\\' [btnfr"'\\]
    | '\\u' HexDigit HexDigit HexDigit HexDigit
    ;

fragment HexDigit
    : [0-9a-fA-F]
    ;

// --- Identifiers ---
IDENTIFIER
    : [a-zA-Z_] [a-zA-Z0-9_]*
    ;

// --- Operators and Punctuation ---
PLUS        : '+';
MINUS       : '-';
STAR        : '*';
SLASH       : '/';
PERCENT     : '%';
EQ          : '=';
EQEQ        : '==';
NEQ         : '!=';
LT          : '<';
LE          : '<=';
GT          : '>';
GE          : '>=';
AMPAMP      : '&&';
PIPEPIPE    : '||';
BANG        : '!';
DOTDOT      : '..';
DOTDOTEQ    : '..=';
ARROW       : '=>';
RARROW      : '->';
COLONCOLON  : '::';
DOT         : '.';
COMMA       : ',';
COLON       : ':';
SEMI        : ';';
LPAREN      : '(';
RPAREN      : ')';
LBRACE      : '{';
RBRACE      : '}';
LBRACK      : '[';
RBRACK      : ']';
PIPE        : '|';
UNDERSCORE  : '_';

// --- Whitespace and Comments ---
WS
    : [ \t\r\n]+ -> skip
    ;

LINE_COMMENT
    : '//' ~[\r\n]* -> skip
    ;

BLOCK_COMMENT
    : '/*' .*? '*/' -> skip
    ;
