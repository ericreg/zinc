grammar zinc;

// ============================================================================
// Parser Rules
// ============================================================================

program
    : statement* EOF
    ;

statement
    : importStatement
    | constDeclaration
    | structDeclaration
    | functionDeclaration
    | asyncFunctionDeclaration
    | variableAssignment
    | channelSendStatement
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
    | selectStatement
    | block
    ;

// --- Import Statement ---
importStatement
    : 'import' importPath ( 'as' IDENTIFIER | '[' importNameList ']' )?
    ;

importPath
    : IDENTIFIER ('/' IDENTIFIER)*
    ;

importNameList
    : IDENTIFIER (',' IDENTIFIER)* ','?
    ;

qualifiedName
    : IDENTIFIER ('.' IDENTIFIER)*
    ;

// --- Const Declaration (global constants) ---
constDeclaration
    : 'const' IDENTIFIER '=' expression
    ;

// --- Struct Declaration ---
structDeclaration
    : 'struct' IDENTIFIER structComposition? '{' structBody '}'
    ;

structComposition
    : '[' orthogonalComposition ']'
    | '[' mergeComposition ']'
    ;

orthogonalComposition
    : qualifiedName ('|' qualifiedName)+
    ;

mergeComposition
    : qualifiedName (',' qualifiedName)+ ','?
    ;

structBody
    : structMember*
    ;

structMember
    : structField
    | functionDeclaration           // method
    ;

structField
    : 'const'? IDENTIFIER ':' (type | expression)
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
    : qualifiedName ('<' typeList '>')?
    | '[' type ']'                  // array type
    | tupleType                     // tuple type
    | '(' typeList? ')' '->' type   // function type
    ;

typeList
    : type (',' type)*
    ;

tupleType
    : '(' type ',' (type (',' type)* ','?)? ')'
    ;

// --- Statements ---
variableAssignment
    : assignmentTarget '=' expression
    ;

assignmentTarget
    : IDENTIFIER
    | memberAccess
    | indexAccess
    | tupleAssignmentTarget
    ;

tupleAssignmentTarget
    : IDENTIFIER ',' IDENTIFIER (',' IDENTIFIER)* ','?
    | '(' IDENTIFIER ',' ')'
    | '(' IDENTIFIER (',' IDENTIFIER)+ ','? ')'
    ;

expressionStatement
    : expression
    ;

ifStatement
    : 'if' expression block ('else' 'if' expression block)* ('else' block)?
    ;

forStatement
    : 'for' forBinding 'in' expression block
    ;

forBinding
    : IDENTIFIER
    | tupleAssignmentTarget
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

selectStatement
    : 'select' '{' selectCase+ '}'
    ;

channelSendStatement
    : IDENTIFIER '<-' expression
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
    | '<-' expression                                           # channelReceiveExpr
    | ('!' | '-' | 'not') expression                            # unaryExpr
    | expression ('*' | '/' | '%') expression                   # multiplicativeExpr
    | expression ('+' | '-') expression                         # additiveExpr
    | expression ('..' | '..=') expression                      # rangeExpr
    | expression ('<' | '<=' | '>' | '>=') expression           # relationalExpr
    | expression ('==' | '!=') expression                       # equalityExpr
    | expression ('and' | '&&') expression                      # logicalAndExpr
    | expression ('or' | '||') expression                       # logicalOrExpr
    | lambdaExpression                                          # lambdaExpr
    | '(' expression ')'                                        # parenExpr
    ;

primaryExpression
    : literal
    | structInstantiation
    | IDENTIFIER
    | 'self'
    | arrayLiteral
    | collectionLiteral
    | tupleLiteral
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

tupleLiteral
    : '(' expression ',' (expression (',' expression)* ','?)? ')'
    ;

collectionLiteral
    : '{' '}'
    | '{' dictEntry (',' dictEntry)* ','? '}'
    | '{' expression (',' expression)* ','? '}'
    ;

dictEntry
    : expression ':' expression
    ;

structInstantiation
    : qualifiedName '{' (fieldInit (','? fieldInit)* ','?)? '}'
    ;

fieldInit
    : IDENTIFIER ':' expression
    ;

argumentList
    : expression (',' expression)*
    ;

selectCase
    : 'case' IDENTIFIER '=' '<-' IDENTIFIER block               # selectReceiveCase
    | 'case' IDENTIFIER '<-' expression block                   # selectSendCase
    | 'default' block                                           # selectDefaultCase
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
CONST       : 'const';
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
DEFAULT     : 'default';
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
LARROW      : '<-';  // Channel send/receive operator (must be before LT)
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
