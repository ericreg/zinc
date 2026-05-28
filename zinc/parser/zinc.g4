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
    | enumDeclaration
    | functionDeclaration
    | asyncFunctionDeclaration
    | outAssignment
    | typedVariableAssignment
    | variableAssignment
    | channelSendStatement
    | ifStatement
    | expressionStatement
    | forStatement
    | whileStatement
    | loopStatement
    | matchStatement
    | returnStatement
    | failStatement
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
    : attributeBlock* 'struct' IDENTIFIER structComposition? '{' structBody '}'
    ;

enumDeclaration
    : 'enum' IDENTIFIER '{' enumBody '}'
    ;

attributeBlock
    : '#[' (expression (',' expression)* ','?)? ']'
    ;

structComposition
    : '[' orthogonalComposition ']'
    | '[' mergeComposition ']'
    ;

orthogonalComposition
    : qualifiedName ('|' qualifiedName)*
    ;

mergeComposition
    : qualifiedName (',' qualifiedName)* ','?
    ;

structBody
    : structMember*
    ;

structMember
    : structField
    | functionDeclaration           // method
    ;

structField
    : 'const'? IDENTIFIER ':' (typeAlternative | expression)
    ;

enumBody
    : enumVariant* functionDeclaration*
    ;

enumVariant
    : IDENTIFIER
    | IDENTIFIER '{' enumVariantFieldType (',' enumVariantFieldType)* ','? '}'
    ;

enumVariantFieldType
    : IDENTIFIER ':' type
    ;

// --- Function Declaration ---
functionDeclaration
    : attributeBlock* 'fn' IDENTIFIER '(' parameterList? ')' ('->' type)? block
    ;

asyncFunctionDeclaration
    : attributeBlock* 'async' IDENTIFIER '(' parameterList? ')' ('->' type)? block
    ;

parameterList
    : parameter (',' parameter)* ','?
    ;

parameter
    : IDENTIFIER (':' typeAlternative)? ('=' expression)?
    ;

typeAlternative
    : type ('|' type)*
    ;

type
    : anonymousStructType
    | qualifiedName ('<' typeList '>')?
    | '[' type ']'                  // array type
    | '(' ')'                       // unit type
    | tupleType                     // tuple type
    | '(' typeList? ')' '->' type   // function type
    ;

typeList
    : type (',' type)* ','?
    ;

tupleType
    : '(' type ',' (type (',' type)* ','?)? ')'
    ;

// --- Statements ---
typedVariableAssignment
    : typedAssignmentTarget ':' type '=' expression
    ;

typedAssignmentTarget
    : IDENTIFIER
    | tupleAssignmentTarget
    ;

variableAssignment
    : assignmentTarget assignmentOperator expression
    ;

assignmentOperator
    : '='
    | '+='
    | '-='
    | '*='
    | '/='
    | '%='
    | '**='
    | '&='
    | '|='
    | '^='
    | '<<='
    | '>>='
    ;

outAssignment
    : IDENTIFIER IDENTIFIER assignmentOperator expression
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
    | resultOptionPattern                       // result/option pattern
    | IDENTIFIER                                // binding pattern
    | enumVariantPattern                        // enum variant pattern
    | rangePattern                              // range pattern (e.g., 0..17)
    | '(' pattern (',' pattern)* ','? ')'       // tuple pattern
    | IDENTIFIER '{' fieldPattern (',' fieldPattern)* ','? '}'  // struct pattern
    ;

resultOptionPattern
    : 'Ok' '(' pattern ','? ')'
    | 'Err' '(' pattern ','? ')'
    | 'Some' '(' pattern ','? ')'
    | 'None'
    ;

enumVariantPattern
    : enumVariantPath
    | enumVariantPath '{' enumVariantFieldPattern (',' enumVariantFieldPattern)* ','? '}'
    ;

rangePattern
    : INTEGER '..' INTEGER
    | INTEGER '..=' INTEGER
    ;

enumVariantPath
    : qualifiedName '.' IDENTIFIER
    ;

enumVariantFieldPattern
    : IDENTIFIER
    | IDENTIFIER ':' IDENTIFIER
    ;

fieldPattern
    : IDENTIFIER (':' pattern)?
    ;

returnStatement
    : 'return' expression?
    ;

failStatement
    : 'fail' expression
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
    | ifExpression                                              # ifExpr
    | tryExpression                                             # tryExpr
    | blockExpression                                           # blockExpr
    | expression '.' IDENTIFIER                                 # memberAccessExpr
    | expression '[' expression ']'                             # indexAccessExpr
    | expression '(' argumentList? ')'                          # functionCallExpr
    | 'await' expression                                        # awaitExpr
    | '<-' expression                                           # channelReceiveExpr
    | ('!' | '-' | 'not') expression                            # unaryExpr
    | <assoc=right> expression '**' expression                  # powerExpr
    | expression ('*' | '/' | '%') expression                   # multiplicativeExpr
    | expression ('+' | '-') expression                         # additiveExpr
    | expression ('<<' | '>>') expression                       # shiftExpr
    | expression '&' expression                                 # bitwiseAndExpr
    | expression '^' expression                                 # bitwiseXorExpr
    | expression '|' expression                                 # bitwiseOrExpr
    | expression ('..' | '..=') expression                      # rangeExpr
    | expression ('<' | '<=' | '>' | '>=') expression           # relationalExpr
    | expression 'in' expression                                # membershipExpr
    | expression ('==' | '!=') expression                       # equalityExpr
    | expression ('and' | '&&') expression                      # logicalAndExpr
    | expression ('or' | '||') expression                       # logicalOrExpr
    | lambdaExpression                                          # lambdaExpr
    | '(' expression ')'                                        # parenExpr
    ;

ifExpression
    : 'if' expression block ('else' (block | ifExpression))?
    ;

tryExpression
    : 'try' block
    ;

blockExpression
    : '{' statement statement+ '}'
    ;

primaryExpression
    : literal
    | unitLiteral
    | anonymousStructLiteral
    | enumVariantConstruction
    | structInstantiation
    | builtinTypeQuery
    | builtinResultOptionConstructor
    | TYPE_KW
    | IDENTIFIER
    | 'self'
    | arrayLiteral
    | collectionLiteral
    | tupleLiteral
    ;

builtinTypeQuery
    : TYPE_KW '(' typeQueryType ')'
    ;

typeQueryType
    : qualifiedName '<' typeList '>'
    ;

builtinResultOptionConstructor
    : 'Ok' '(' expression ','? ')'
    | 'Err' '(' expression ','? ')'
    | 'Some' '(' expression ','? ')'
    | 'None'
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

unitLiteral
    : '(' ')'
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

anonymousStructType
    : 'struct' '{' anonymousStructFieldType* '}'
    ;

anonymousStructFieldType
    : IDENTIFIER ':' type
    ;

anonymousStructLiteral
    : 'struct' '{' (structFieldEntry (','? structFieldEntry)* ','?)? '}'
    ;

dictEntry
    : expression ':' expression
    ;

structInstantiation
    : qualifiedName '{' (structFieldEntry (','? structFieldEntry)* ','?)? '}'
    ;

enumVariantConstruction
    : enumVariantPath '{' (fieldInit (','? fieldInit)* ','?)? '}'
    ;

fieldInit
    : IDENTIFIER ':' expression
    ;

structFieldEntry
    : fieldInit
    | fieldSpread
    ;

fieldSpread
    : '..' expression
    ;

argumentList
    : argument (',' argument)* ','?
    ;

argument
    : IDENTIFIER '=' expression
    | '..' expression
    | expression
    ;

selectCase
    : 'case' (selectReceiveBinding '=')? '<-' expression block  # selectReceiveCase
    | 'case' IDENTIFIER '<-' expression block                   # selectSendCase
    | 'default' block                                           # selectDefaultCase
    ;

selectReceiveBinding
    : IDENTIFIER
    | tupleAssignmentTarget
    ;

lambdaExpression
    : 'fn' '(' parameterList? ')' block
    ;

// ============================================================================
// Lexer Rules
// ============================================================================

// --- Keywords ---
USE         : 'use';
STRUCT      : 'struct';
ENUM        : 'enum';
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
TYPE_KW     : 'type';
TRY         : 'try';
FAIL        : 'fail';
OK          : 'Ok';
ERR         : 'Err';
SOME        : 'Some';
NONE        : 'None';

FLOAT
    : DecLiteral '.' DecLiteral FloatExponent? FloatSuffix?
    | DecLiteral '.' {self._input.LA(1) != ord('.') and self._input.LA(1) != ord('_') and not (ord('0') <= self._input.LA(1) <= ord('9')) and not (ord('A') <= self._input.LA(1) <= ord('Z')) and not (ord('a') <= self._input.LA(1) <= ord('z'))}?
    | DecLiteral FloatExponent FloatSuffix?
    | DecLiteral FloatSuffix
    ;

INTEGER
    : DecLiteral IntegerSuffix?
    | BinLiteral IntegerSuffix?
    | OctLiteral IntegerSuffix?
    | HexLiteral IntegerSuffix?
    ;

STRING
    : '"' (~["\\\r\n] | EscapeSequence)* '"'
    | '\'' (~['\\\r\n] | EscapeSequence)* '\''
    | '`' ('``' | ~[`])* '`'
    ;

fragment EscapeSequence
    : '\\' [btnfr"'\\]
    | '\\u' HexDigit HexDigit HexDigit HexDigit
    ;

fragment HexDigit
    : [0-9a-fA-F]
    ;

fragment DecLiteral
    : [0-9] [0-9_]*
    ;

fragment BinLiteral
    : '0b' '_'* [01] [01_]*
    ;

fragment OctLiteral
    : '0o' '_'* [0-7] [0-7_]*
    ;

fragment HexLiteral
    : '0x' '_'* [0-9a-fA-F] [0-9a-fA-F_]*
    ;

fragment IntegerSuffix
    : 'u8'
    | 'i8'
    | 'u16'
    | 'i16'
    | 'u32'
    | 'i32'
    | 'u64'
    | 'i64'
    | 'u128'
    | 'i128'
    | 'usize'
    | 'isize'
    ;

fragment FloatSuffix
    : 'f32'
    | 'f64'
    ;

fragment FloatExponent
    : [eE] [+-]? '_'* [0-9] [0-9_]*
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
REMOVED_SUPER_ASSIGN: '<<-';
SHLEQ       : '<<=';
SHREQ       : '>>=';
AMPEQ       : '&=';
PIPEEQ      : '|=';
CARETEQ     : '^=';
SHL         : '<<';
SHR         : '>>';
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
AMP         : '&';
BANG        : '!';
CARET       : '^';
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
