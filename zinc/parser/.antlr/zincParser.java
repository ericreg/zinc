// Generated from /workspaces/zinc/zinc/parser/zinc.g4 by ANTLR 4.13.1
import org.antlr.v4.runtime.atn.*;
import org.antlr.v4.runtime.dfa.DFA;
import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.misc.*;
import org.antlr.v4.runtime.tree.*;
import java.util.List;
import java.util.Iterator;
import java.util.ArrayList;

@SuppressWarnings({"all", "warnings", "unchecked", "unused", "cast", "CheckReturnValue"})
public class zincParser extends Parser {
	static { RuntimeMetaData.checkVersion("4.13.1", RuntimeMetaData.VERSION); }

	protected static final DFA[] _decisionToDFA;
	protected static final PredictionContextCache _sharedContextCache =
		new PredictionContextCache();
	public static final int
		USE=1, STRUCT=2, FN=3, ASYNC=4, AWAIT=5, IF=6, ELSE=7, FOR=8, IN=9, WHILE=10, 
		LOOP=11, MATCH=12, RETURN=13, BREAK=14, CONTINUE=15, TRUE=16, FALSE=17, 
		NIL=18, AND=19, OR=20, NOT=21, SELF=22, SELECT=23, CASE=24, INTEGER=25, 
		FLOAT=26, STRING=27, IDENTIFIER=28, PLUS=29, MINUS=30, STAR=31, SLASH=32, 
		PERCENT=33, EQ=34, EQEQ=35, NEQ=36, LT=37, LE=38, GT=39, GE=40, AMPAMP=41, 
		PIPEPIPE=42, BANG=43, DOTDOT=44, DOTDOTEQ=45, ARROW=46, RARROW=47, COLONCOLON=48, 
		DOT=49, COMMA=50, COLON=51, SEMI=52, LPAREN=53, RPAREN=54, LBRACE=55, 
		RBRACE=56, LBRACK=57, RBRACK=58, PIPE=59, UNDERSCORE=60, WS=61, LINE_COMMENT=62, 
		BLOCK_COMMENT=63;
	public static final int
		RULE_program = 0, RULE_statement = 1, RULE_functionDeclaration = 2, RULE_parameterList = 3, 
		RULE_parameter = 4, RULE_type = 5, RULE_typeList = 6, RULE_variableAssignment = 7, 
		RULE_assignmentTarget = 8, RULE_expressionStatement = 9, RULE_matchStatement = 10, 
		RULE_matchArm = 11, RULE_pattern = 12, RULE_rangePattern = 13, RULE_fieldPattern = 14, 
		RULE_returnStatement = 15, RULE_breakStatement = 16, RULE_continueStatement = 17, 
		RULE_block = 18, RULE_expression = 19, RULE_primaryExpression = 20, RULE_literal = 21, 
		RULE_booleanLiteral = 22;
	private static String[] makeRuleNames() {
		return new String[] {
			"program", "statement", "functionDeclaration", "parameterList", "parameter", 
			"type", "typeList", "variableAssignment", "assignmentTarget", "expressionStatement", 
			"matchStatement", "matchArm", "pattern", "rangePattern", "fieldPattern", 
			"returnStatement", "breakStatement", "continueStatement", "block", "expression", 
			"primaryExpression", "literal", "booleanLiteral"
		};
	}
	public static final String[] ruleNames = makeRuleNames();

	private static String[] makeLiteralNames() {
		return new String[] {
			null, "'use'", "'struct'", "'fn'", "'async'", "'await'", "'if'", "'else'", 
			"'for'", "'in'", "'while'", "'loop'", "'match'", "'return'", "'break'", 
			"'continue'", "'true'", "'false'", "'nil'", "'and'", "'or'", "'not'", 
			"'self'", "'select'", "'case'", null, null, null, null, "'+'", "'-'", 
			"'*'", "'/'", "'%'", "'='", "'=='", "'!='", "'<'", "'<='", "'>'", "'>='", 
			"'&&'", "'||'", "'!'", "'..'", "'..='", "'=>'", "'->'", "'::'", "'.'", 
			"','", "':'", "';'", "'('", "')'", "'{'", "'}'", "'['", "']'", "'|'", 
			"'_'"
		};
	}
	private static final String[] _LITERAL_NAMES = makeLiteralNames();
	private static String[] makeSymbolicNames() {
		return new String[] {
			null, "USE", "STRUCT", "FN", "ASYNC", "AWAIT", "IF", "ELSE", "FOR", "IN", 
			"WHILE", "LOOP", "MATCH", "RETURN", "BREAK", "CONTINUE", "TRUE", "FALSE", 
			"NIL", "AND", "OR", "NOT", "SELF", "SELECT", "CASE", "INTEGER", "FLOAT", 
			"STRING", "IDENTIFIER", "PLUS", "MINUS", "STAR", "SLASH", "PERCENT", 
			"EQ", "EQEQ", "NEQ", "LT", "LE", "GT", "GE", "AMPAMP", "PIPEPIPE", "BANG", 
			"DOTDOT", "DOTDOTEQ", "ARROW", "RARROW", "COLONCOLON", "DOT", "COMMA", 
			"COLON", "SEMI", "LPAREN", "RPAREN", "LBRACE", "RBRACE", "LBRACK", "RBRACK", 
			"PIPE", "UNDERSCORE", "WS", "LINE_COMMENT", "BLOCK_COMMENT"
		};
	}
	private static final String[] _SYMBOLIC_NAMES = makeSymbolicNames();
	public static final Vocabulary VOCABULARY = new VocabularyImpl(_LITERAL_NAMES, _SYMBOLIC_NAMES);

	/**
	 * @deprecated Use {@link #VOCABULARY} instead.
	 */
	@Deprecated
	public static final String[] tokenNames;
	static {
		tokenNames = new String[_SYMBOLIC_NAMES.length];
		for (int i = 0; i < tokenNames.length; i++) {
			tokenNames[i] = VOCABULARY.getLiteralName(i);
			if (tokenNames[i] == null) {
				tokenNames[i] = VOCABULARY.getSymbolicName(i);
			}

			if (tokenNames[i] == null) {
				tokenNames[i] = "<INVALID>";
			}
		}
	}

	@Override
	@Deprecated
	public String[] getTokenNames() {
		return tokenNames;
	}

	@Override

	public Vocabulary getVocabulary() {
		return VOCABULARY;
	}

	@Override
	public String getGrammarFileName() { return "zinc.g4"; }

	@Override
	public String[] getRuleNames() { return ruleNames; }

	@Override
	public String getSerializedATN() { return _serializedATN; }

	@Override
	public ATN getATN() { return _ATN; }

	public zincParser(TokenStream input) {
		super(input);
		_interp = new ParserATNSimulator(this,_ATN,_decisionToDFA,_sharedContextCache);
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ProgramContext extends ParserRuleContext {
		public TerminalNode EOF() { return getToken(zincParser.EOF, 0); }
		public List<StatementContext> statement() {
			return getRuleContexts(StatementContext.class);
		}
		public StatementContext statement(int i) {
			return getRuleContext(StatementContext.class,i);
		}
		public ProgramContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_program; }
	}

	public final ProgramContext program() throws RecognitionException {
		ProgramContext _localctx = new ProgramContext(_ctx, getState());
		enterRule(_localctx, 0, RULE_program);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(49);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==FN || _la==IDENTIFIER) {
				{
				{
				setState(46);
				statement();
				}
				}
				setState(51);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			setState(52);
			match(EOF);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class StatementContext extends ParserRuleContext {
		public FunctionDeclarationContext functionDeclaration() {
			return getRuleContext(FunctionDeclarationContext.class,0);
		}
		public VariableAssignmentContext variableAssignment() {
			return getRuleContext(VariableAssignmentContext.class,0);
		}
		public StatementContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_statement; }
	}

	public final StatementContext statement() throws RecognitionException {
		StatementContext _localctx = new StatementContext(_ctx, getState());
		enterRule(_localctx, 2, RULE_statement);
		try {
			setState(56);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case FN:
				enterOuterAlt(_localctx, 1);
				{
				setState(54);
				functionDeclaration();
				}
				break;
			case IDENTIFIER:
				enterOuterAlt(_localctx, 2);
				{
				setState(55);
				variableAssignment();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class FunctionDeclarationContext extends ParserRuleContext {
		public TerminalNode FN() { return getToken(zincParser.FN, 0); }
		public TerminalNode IDENTIFIER() { return getToken(zincParser.IDENTIFIER, 0); }
		public TerminalNode LPAREN() { return getToken(zincParser.LPAREN, 0); }
		public TerminalNode RPAREN() { return getToken(zincParser.RPAREN, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public ParameterListContext parameterList() {
			return getRuleContext(ParameterListContext.class,0);
		}
		public FunctionDeclarationContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_functionDeclaration; }
	}

	public final FunctionDeclarationContext functionDeclaration() throws RecognitionException {
		FunctionDeclarationContext _localctx = new FunctionDeclarationContext(_ctx, getState());
		enterRule(_localctx, 4, RULE_functionDeclaration);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(58);
			match(FN);
			setState(59);
			match(IDENTIFIER);
			setState(60);
			match(LPAREN);
			setState(62);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==IDENTIFIER) {
				{
				setState(61);
				parameterList();
				}
			}

			setState(64);
			match(RPAREN);
			setState(65);
			block();
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ParameterListContext extends ParserRuleContext {
		public List<ParameterContext> parameter() {
			return getRuleContexts(ParameterContext.class);
		}
		public ParameterContext parameter(int i) {
			return getRuleContext(ParameterContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(zincParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(zincParser.COMMA, i);
		}
		public ParameterListContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_parameterList; }
	}

	public final ParameterListContext parameterList() throws RecognitionException {
		ParameterListContext _localctx = new ParameterListContext(_ctx, getState());
		enterRule(_localctx, 6, RULE_parameterList);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(67);
			parameter();
			setState(72);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==COMMA) {
				{
				{
				setState(68);
				match(COMMA);
				setState(69);
				parameter();
				}
				}
				setState(74);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ParameterContext extends ParserRuleContext {
		public TerminalNode IDENTIFIER() { return getToken(zincParser.IDENTIFIER, 0); }
		public TerminalNode COLON() { return getToken(zincParser.COLON, 0); }
		public TypeContext type() {
			return getRuleContext(TypeContext.class,0);
		}
		public ParameterContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_parameter; }
	}

	public final ParameterContext parameter() throws RecognitionException {
		ParameterContext _localctx = new ParameterContext(_ctx, getState());
		enterRule(_localctx, 8, RULE_parameter);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(75);
			match(IDENTIFIER);
			setState(78);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COLON) {
				{
				setState(76);
				match(COLON);
				setState(77);
				type();
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class TypeContext extends ParserRuleContext {
		public TerminalNode IDENTIFIER() { return getToken(zincParser.IDENTIFIER, 0); }
		public TerminalNode LT() { return getToken(zincParser.LT, 0); }
		public TypeListContext typeList() {
			return getRuleContext(TypeListContext.class,0);
		}
		public TerminalNode GT() { return getToken(zincParser.GT, 0); }
		public TerminalNode LBRACK() { return getToken(zincParser.LBRACK, 0); }
		public TypeContext type() {
			return getRuleContext(TypeContext.class,0);
		}
		public TerminalNode RBRACK() { return getToken(zincParser.RBRACK, 0); }
		public TerminalNode LPAREN() { return getToken(zincParser.LPAREN, 0); }
		public TerminalNode RPAREN() { return getToken(zincParser.RPAREN, 0); }
		public TerminalNode RARROW() { return getToken(zincParser.RARROW, 0); }
		public TypeContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_type; }
	}

	public final TypeContext type() throws RecognitionException {
		TypeContext _localctx = new TypeContext(_ctx, getState());
		enterRule(_localctx, 10, RULE_type);
		int _la;
		try {
			setState(98);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case IDENTIFIER:
				enterOuterAlt(_localctx, 1);
				{
				setState(80);
				match(IDENTIFIER);
				setState(85);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==LT) {
					{
					setState(81);
					match(LT);
					setState(82);
					typeList();
					setState(83);
					match(GT);
					}
				}

				}
				break;
			case LBRACK:
				enterOuterAlt(_localctx, 2);
				{
				setState(87);
				match(LBRACK);
				setState(88);
				type();
				setState(89);
				match(RBRACK);
				}
				break;
			case LPAREN:
				enterOuterAlt(_localctx, 3);
				{
				setState(91);
				match(LPAREN);
				setState(93);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 153122387599032320L) != 0)) {
					{
					setState(92);
					typeList();
					}
				}

				setState(95);
				match(RPAREN);
				setState(96);
				match(RARROW);
				setState(97);
				type();
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class TypeListContext extends ParserRuleContext {
		public List<TypeContext> type() {
			return getRuleContexts(TypeContext.class);
		}
		public TypeContext type(int i) {
			return getRuleContext(TypeContext.class,i);
		}
		public List<TerminalNode> COMMA() { return getTokens(zincParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(zincParser.COMMA, i);
		}
		public TypeListContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_typeList; }
	}

	public final TypeListContext typeList() throws RecognitionException {
		TypeListContext _localctx = new TypeListContext(_ctx, getState());
		enterRule(_localctx, 12, RULE_typeList);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(100);
			type();
			setState(105);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==COMMA) {
				{
				{
				setState(101);
				match(COMMA);
				setState(102);
				type();
				}
				}
				setState(107);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class VariableAssignmentContext extends ParserRuleContext {
		public AssignmentTargetContext assignmentTarget() {
			return getRuleContext(AssignmentTargetContext.class,0);
		}
		public TerminalNode EQ() { return getToken(zincParser.EQ, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public VariableAssignmentContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_variableAssignment; }
	}

	public final VariableAssignmentContext variableAssignment() throws RecognitionException {
		VariableAssignmentContext _localctx = new VariableAssignmentContext(_ctx, getState());
		enterRule(_localctx, 14, RULE_variableAssignment);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(108);
			assignmentTarget();
			setState(109);
			match(EQ);
			setState(110);
			expression(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class AssignmentTargetContext extends ParserRuleContext {
		public TerminalNode IDENTIFIER() { return getToken(zincParser.IDENTIFIER, 0); }
		public AssignmentTargetContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_assignmentTarget; }
	}

	public final AssignmentTargetContext assignmentTarget() throws RecognitionException {
		AssignmentTargetContext _localctx = new AssignmentTargetContext(_ctx, getState());
		enterRule(_localctx, 16, RULE_assignmentTarget);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(112);
			match(IDENTIFIER);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ExpressionStatementContext extends ParserRuleContext {
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public ExpressionStatementContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_expressionStatement; }
	}

	public final ExpressionStatementContext expressionStatement() throws RecognitionException {
		ExpressionStatementContext _localctx = new ExpressionStatementContext(_ctx, getState());
		enterRule(_localctx, 18, RULE_expressionStatement);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(114);
			expression(0);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class MatchStatementContext extends ParserRuleContext {
		public TerminalNode MATCH() { return getToken(zincParser.MATCH, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode LBRACE() { return getToken(zincParser.LBRACE, 0); }
		public List<MatchArmContext> matchArm() {
			return getRuleContexts(MatchArmContext.class);
		}
		public MatchArmContext matchArm(int i) {
			return getRuleContext(MatchArmContext.class,i);
		}
		public TerminalNode RBRACE() { return getToken(zincParser.RBRACE, 0); }
		public List<TerminalNode> COMMA() { return getTokens(zincParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(zincParser.COMMA, i);
		}
		public MatchStatementContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_matchStatement; }
	}

	public final MatchStatementContext matchStatement() throws RecognitionException {
		MatchStatementContext _localctx = new MatchStatementContext(_ctx, getState());
		enterRule(_localctx, 20, RULE_matchStatement);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(116);
			match(MATCH);
			setState(117);
			expression(0);
			setState(118);
			match(LBRACE);
			setState(119);
			matchArm();
			setState(124);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,9,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					{
					{
					setState(120);
					match(COMMA);
					setState(121);
					matchArm();
					}
					} 
				}
				setState(126);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,9,_ctx);
			}
			setState(128);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COMMA) {
				{
				setState(127);
				match(COMMA);
				}
			}

			setState(130);
			match(RBRACE);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class MatchArmContext extends ParserRuleContext {
		public PatternContext pattern() {
			return getRuleContext(PatternContext.class,0);
		}
		public TerminalNode ARROW() { return getToken(zincParser.ARROW, 0); }
		public BlockContext block() {
			return getRuleContext(BlockContext.class,0);
		}
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public MatchArmContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_matchArm; }
	}

	public final MatchArmContext matchArm() throws RecognitionException {
		MatchArmContext _localctx = new MatchArmContext(_ctx, getState());
		enterRule(_localctx, 22, RULE_matchArm);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(132);
			pattern();
			setState(133);
			match(ARROW);
			setState(136);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case LBRACE:
				{
				setState(134);
				block();
				}
				break;
			case AWAIT:
			case TRUE:
			case FALSE:
			case NIL:
			case NOT:
			case INTEGER:
			case FLOAT:
			case STRING:
			case IDENTIFIER:
			case MINUS:
			case BANG:
			case LPAREN:
				{
				setState(135);
				expression(0);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class PatternContext extends ParserRuleContext {
		public TerminalNode UNDERSCORE() { return getToken(zincParser.UNDERSCORE, 0); }
		public LiteralContext literal() {
			return getRuleContext(LiteralContext.class,0);
		}
		public TerminalNode IDENTIFIER() { return getToken(zincParser.IDENTIFIER, 0); }
		public RangePatternContext rangePattern() {
			return getRuleContext(RangePatternContext.class,0);
		}
		public TerminalNode LPAREN() { return getToken(zincParser.LPAREN, 0); }
		public List<PatternContext> pattern() {
			return getRuleContexts(PatternContext.class);
		}
		public PatternContext pattern(int i) {
			return getRuleContext(PatternContext.class,i);
		}
		public TerminalNode RPAREN() { return getToken(zincParser.RPAREN, 0); }
		public List<TerminalNode> COMMA() { return getTokens(zincParser.COMMA); }
		public TerminalNode COMMA(int i) {
			return getToken(zincParser.COMMA, i);
		}
		public TerminalNode LBRACE() { return getToken(zincParser.LBRACE, 0); }
		public List<FieldPatternContext> fieldPattern() {
			return getRuleContexts(FieldPatternContext.class);
		}
		public FieldPatternContext fieldPattern(int i) {
			return getRuleContext(FieldPatternContext.class,i);
		}
		public TerminalNode RBRACE() { return getToken(zincParser.RBRACE, 0); }
		public PatternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_pattern; }
	}

	public final PatternContext pattern() throws RecognitionException {
		PatternContext _localctx = new PatternContext(_ctx, getState());
		enterRule(_localctx, 24, RULE_pattern);
		int _la;
		try {
			int _alt;
			setState(168);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,15,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(138);
				match(UNDERSCORE);
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(139);
				literal();
				}
				break;
			case 3:
				enterOuterAlt(_localctx, 3);
				{
				setState(140);
				match(IDENTIFIER);
				}
				break;
			case 4:
				enterOuterAlt(_localctx, 4);
				{
				setState(141);
				rangePattern();
				}
				break;
			case 5:
				enterOuterAlt(_localctx, 5);
				{
				setState(142);
				match(LPAREN);
				setState(143);
				pattern();
				setState(148);
				_errHandler.sync(this);
				_la = _input.LA(1);
				while (_la==COMMA) {
					{
					{
					setState(144);
					match(COMMA);
					setState(145);
					pattern();
					}
					}
					setState(150);
					_errHandler.sync(this);
					_la = _input.LA(1);
				}
				setState(151);
				match(RPAREN);
				}
				break;
			case 6:
				enterOuterAlt(_localctx, 6);
				{
				setState(153);
				match(IDENTIFIER);
				setState(154);
				match(LBRACE);
				setState(155);
				fieldPattern();
				setState(160);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,13,_ctx);
				while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
					if ( _alt==1 ) {
						{
						{
						setState(156);
						match(COMMA);
						setState(157);
						fieldPattern();
						}
						} 
					}
					setState(162);
					_errHandler.sync(this);
					_alt = getInterpreter().adaptivePredict(_input,13,_ctx);
				}
				setState(164);
				_errHandler.sync(this);
				_la = _input.LA(1);
				if (_la==COMMA) {
					{
					setState(163);
					match(COMMA);
					}
				}

				setState(166);
				match(RBRACE);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class RangePatternContext extends ParserRuleContext {
		public List<TerminalNode> INTEGER() { return getTokens(zincParser.INTEGER); }
		public TerminalNode INTEGER(int i) {
			return getToken(zincParser.INTEGER, i);
		}
		public TerminalNode DOTDOT() { return getToken(zincParser.DOTDOT, 0); }
		public TerminalNode DOTDOTEQ() { return getToken(zincParser.DOTDOTEQ, 0); }
		public RangePatternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_rangePattern; }
	}

	public final RangePatternContext rangePattern() throws RecognitionException {
		RangePatternContext _localctx = new RangePatternContext(_ctx, getState());
		enterRule(_localctx, 26, RULE_rangePattern);
		try {
			setState(176);
			_errHandler.sync(this);
			switch ( getInterpreter().adaptivePredict(_input,16,_ctx) ) {
			case 1:
				enterOuterAlt(_localctx, 1);
				{
				setState(170);
				match(INTEGER);
				setState(171);
				match(DOTDOT);
				setState(172);
				match(INTEGER);
				}
				break;
			case 2:
				enterOuterAlt(_localctx, 2);
				{
				setState(173);
				match(INTEGER);
				setState(174);
				match(DOTDOTEQ);
				setState(175);
				match(INTEGER);
				}
				break;
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class FieldPatternContext extends ParserRuleContext {
		public TerminalNode IDENTIFIER() { return getToken(zincParser.IDENTIFIER, 0); }
		public TerminalNode COLON() { return getToken(zincParser.COLON, 0); }
		public PatternContext pattern() {
			return getRuleContext(PatternContext.class,0);
		}
		public FieldPatternContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_fieldPattern; }
	}

	public final FieldPatternContext fieldPattern() throws RecognitionException {
		FieldPatternContext _localctx = new FieldPatternContext(_ctx, getState());
		enterRule(_localctx, 28, RULE_fieldPattern);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(178);
			match(IDENTIFIER);
			setState(181);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if (_la==COLON) {
				{
				setState(179);
				match(COLON);
				setState(180);
				pattern();
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ReturnStatementContext extends ParserRuleContext {
		public TerminalNode RETURN() { return getToken(zincParser.RETURN, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public ReturnStatementContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_returnStatement; }
	}

	public final ReturnStatementContext returnStatement() throws RecognitionException {
		ReturnStatementContext _localctx = new ReturnStatementContext(_ctx, getState());
		enterRule(_localctx, 30, RULE_returnStatement);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(183);
			match(RETURN);
			setState(185);
			_errHandler.sync(this);
			_la = _input.LA(1);
			if ((((_la) & ~0x3f) == 0 && ((1L << _la) & 9015996927377440L) != 0)) {
				{
				setState(184);
				expression(0);
				}
			}

			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class BreakStatementContext extends ParserRuleContext {
		public TerminalNode BREAK() { return getToken(zincParser.BREAK, 0); }
		public BreakStatementContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_breakStatement; }
	}

	public final BreakStatementContext breakStatement() throws RecognitionException {
		BreakStatementContext _localctx = new BreakStatementContext(_ctx, getState());
		enterRule(_localctx, 32, RULE_breakStatement);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(187);
			match(BREAK);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ContinueStatementContext extends ParserRuleContext {
		public TerminalNode CONTINUE() { return getToken(zincParser.CONTINUE, 0); }
		public ContinueStatementContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_continueStatement; }
	}

	public final ContinueStatementContext continueStatement() throws RecognitionException {
		ContinueStatementContext _localctx = new ContinueStatementContext(_ctx, getState());
		enterRule(_localctx, 34, RULE_continueStatement);
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(189);
			match(CONTINUE);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class BlockContext extends ParserRuleContext {
		public TerminalNode LBRACE() { return getToken(zincParser.LBRACE, 0); }
		public TerminalNode RBRACE() { return getToken(zincParser.RBRACE, 0); }
		public List<StatementContext> statement() {
			return getRuleContexts(StatementContext.class);
		}
		public StatementContext statement(int i) {
			return getRuleContext(StatementContext.class,i);
		}
		public BlockContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_block; }
	}

	public final BlockContext block() throws RecognitionException {
		BlockContext _localctx = new BlockContext(_ctx, getState());
		enterRule(_localctx, 36, RULE_block);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(191);
			match(LBRACE);
			setState(195);
			_errHandler.sync(this);
			_la = _input.LA(1);
			while (_la==FN || _la==IDENTIFIER) {
				{
				{
				setState(192);
				statement();
				}
				}
				setState(197);
				_errHandler.sync(this);
				_la = _input.LA(1);
			}
			setState(198);
			match(RBRACE);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class ExpressionContext extends ParserRuleContext {
		public ExpressionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_expression; }
	 
		public ExpressionContext() { }
		public void copyFrom(ExpressionContext ctx) {
			super.copyFrom(ctx);
		}
	}
	@SuppressWarnings("CheckReturnValue")
	public static class LogicalAndExprContext extends ExpressionContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode AND() { return getToken(zincParser.AND, 0); }
		public TerminalNode AMPAMP() { return getToken(zincParser.AMPAMP, 0); }
		public LogicalAndExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class AdditiveExprContext extends ExpressionContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode PLUS() { return getToken(zincParser.PLUS, 0); }
		public TerminalNode MINUS() { return getToken(zincParser.MINUS, 0); }
		public AdditiveExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class AwaitExprContext extends ExpressionContext {
		public TerminalNode AWAIT() { return getToken(zincParser.AWAIT, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public AwaitExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class RelationalExprContext extends ExpressionContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode LT() { return getToken(zincParser.LT, 0); }
		public TerminalNode LE() { return getToken(zincParser.LE, 0); }
		public TerminalNode GT() { return getToken(zincParser.GT, 0); }
		public TerminalNode GE() { return getToken(zincParser.GE, 0); }
		public RelationalExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class ParenExprContext extends ExpressionContext {
		public TerminalNode LPAREN() { return getToken(zincParser.LPAREN, 0); }
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode RPAREN() { return getToken(zincParser.RPAREN, 0); }
		public ParenExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class LogicalOrExprContext extends ExpressionContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode OR() { return getToken(zincParser.OR, 0); }
		public TerminalNode PIPEPIPE() { return getToken(zincParser.PIPEPIPE, 0); }
		public LogicalOrExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class UnaryExprContext extends ExpressionContext {
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode BANG() { return getToken(zincParser.BANG, 0); }
		public TerminalNode MINUS() { return getToken(zincParser.MINUS, 0); }
		public TerminalNode NOT() { return getToken(zincParser.NOT, 0); }
		public UnaryExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class PrimaryExprContext extends ExpressionContext {
		public PrimaryExpressionContext primaryExpression() {
			return getRuleContext(PrimaryExpressionContext.class,0);
		}
		public PrimaryExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class IndexAccessExprContext extends ExpressionContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode LBRACK() { return getToken(zincParser.LBRACK, 0); }
		public TerminalNode RBRACK() { return getToken(zincParser.RBRACK, 0); }
		public IndexAccessExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class MemberAccessExprContext extends ExpressionContext {
		public ExpressionContext expression() {
			return getRuleContext(ExpressionContext.class,0);
		}
		public TerminalNode DOT() { return getToken(zincParser.DOT, 0); }
		public TerminalNode IDENTIFIER() { return getToken(zincParser.IDENTIFIER, 0); }
		public MemberAccessExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class MultiplicativeExprContext extends ExpressionContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode STAR() { return getToken(zincParser.STAR, 0); }
		public TerminalNode SLASH() { return getToken(zincParser.SLASH, 0); }
		public TerminalNode PERCENT() { return getToken(zincParser.PERCENT, 0); }
		public MultiplicativeExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class RangeExprContext extends ExpressionContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode DOTDOT() { return getToken(zincParser.DOTDOT, 0); }
		public TerminalNode DOTDOTEQ() { return getToken(zincParser.DOTDOTEQ, 0); }
		public RangeExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}
	@SuppressWarnings("CheckReturnValue")
	public static class EqualityExprContext extends ExpressionContext {
		public List<ExpressionContext> expression() {
			return getRuleContexts(ExpressionContext.class);
		}
		public ExpressionContext expression(int i) {
			return getRuleContext(ExpressionContext.class,i);
		}
		public TerminalNode EQEQ() { return getToken(zincParser.EQEQ, 0); }
		public TerminalNode NEQ() { return getToken(zincParser.NEQ, 0); }
		public EqualityExprContext(ExpressionContext ctx) { copyFrom(ctx); }
	}

	public final ExpressionContext expression() throws RecognitionException {
		return expression(0);
	}

	private ExpressionContext expression(int _p) throws RecognitionException {
		ParserRuleContext _parentctx = _ctx;
		int _parentState = getState();
		ExpressionContext _localctx = new ExpressionContext(_ctx, _parentState);
		ExpressionContext _prevctx = _localctx;
		int _startState = 38;
		enterRecursionRule(_localctx, 38, RULE_expression, _p);
		int _la;
		try {
			int _alt;
			enterOuterAlt(_localctx, 1);
			{
			setState(210);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case TRUE:
			case FALSE:
			case NIL:
			case INTEGER:
			case FLOAT:
			case STRING:
			case IDENTIFIER:
				{
				_localctx = new PrimaryExprContext(_localctx);
				_ctx = _localctx;
				_prevctx = _localctx;

				setState(201);
				primaryExpression();
				}
				break;
			case AWAIT:
				{
				_localctx = new AwaitExprContext(_localctx);
				_ctx = _localctx;
				_prevctx = _localctx;
				setState(202);
				match(AWAIT);
				setState(203);
				expression(10);
				}
				break;
			case NOT:
			case MINUS:
			case BANG:
				{
				_localctx = new UnaryExprContext(_localctx);
				_ctx = _localctx;
				_prevctx = _localctx;
				setState(204);
				_la = _input.LA(1);
				if ( !((((_la) & ~0x3f) == 0 && ((1L << _la) & 8797168861184L) != 0)) ) {
				_errHandler.recoverInline(this);
				}
				else {
					if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
					_errHandler.reportMatch(this);
					consume();
				}
				setState(205);
				expression(9);
				}
				break;
			case LPAREN:
				{
				_localctx = new ParenExprContext(_localctx);
				_ctx = _localctx;
				_prevctx = _localctx;
				setState(206);
				match(LPAREN);
				setState(207);
				expression(0);
				setState(208);
				match(RPAREN);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
			_ctx.stop = _input.LT(-1);
			setState(243);
			_errHandler.sync(this);
			_alt = getInterpreter().adaptivePredict(_input,22,_ctx);
			while ( _alt!=2 && _alt!=org.antlr.v4.runtime.atn.ATN.INVALID_ALT_NUMBER ) {
				if ( _alt==1 ) {
					if ( _parseListeners!=null ) triggerExitRuleEvent();
					_prevctx = _localctx;
					{
					setState(241);
					_errHandler.sync(this);
					switch ( getInterpreter().adaptivePredict(_input,21,_ctx) ) {
					case 1:
						{
						_localctx = new MultiplicativeExprContext(new ExpressionContext(_parentctx, _parentState));
						pushNewRecursionContext(_localctx, _startState, RULE_expression);
						setState(212);
						if (!(precpred(_ctx, 8))) throw new FailedPredicateException(this, "precpred(_ctx, 8)");
						setState(213);
						_la = _input.LA(1);
						if ( !((((_la) & ~0x3f) == 0 && ((1L << _la) & 15032385536L) != 0)) ) {
						_errHandler.recoverInline(this);
						}
						else {
							if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
							_errHandler.reportMatch(this);
							consume();
						}
						setState(214);
						expression(9);
						}
						break;
					case 2:
						{
						_localctx = new AdditiveExprContext(new ExpressionContext(_parentctx, _parentState));
						pushNewRecursionContext(_localctx, _startState, RULE_expression);
						setState(215);
						if (!(precpred(_ctx, 7))) throw new FailedPredicateException(this, "precpred(_ctx, 7)");
						setState(216);
						_la = _input.LA(1);
						if ( !(_la==PLUS || _la==MINUS) ) {
						_errHandler.recoverInline(this);
						}
						else {
							if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
							_errHandler.reportMatch(this);
							consume();
						}
						setState(217);
						expression(8);
						}
						break;
					case 3:
						{
						_localctx = new RangeExprContext(new ExpressionContext(_parentctx, _parentState));
						pushNewRecursionContext(_localctx, _startState, RULE_expression);
						setState(218);
						if (!(precpred(_ctx, 6))) throw new FailedPredicateException(this, "precpred(_ctx, 6)");
						setState(219);
						_la = _input.LA(1);
						if ( !(_la==DOTDOT || _la==DOTDOTEQ) ) {
						_errHandler.recoverInline(this);
						}
						else {
							if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
							_errHandler.reportMatch(this);
							consume();
						}
						setState(220);
						expression(7);
						}
						break;
					case 4:
						{
						_localctx = new RelationalExprContext(new ExpressionContext(_parentctx, _parentState));
						pushNewRecursionContext(_localctx, _startState, RULE_expression);
						setState(221);
						if (!(precpred(_ctx, 5))) throw new FailedPredicateException(this, "precpred(_ctx, 5)");
						setState(222);
						_la = _input.LA(1);
						if ( !((((_la) & ~0x3f) == 0 && ((1L << _la) & 2061584302080L) != 0)) ) {
						_errHandler.recoverInline(this);
						}
						else {
							if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
							_errHandler.reportMatch(this);
							consume();
						}
						setState(223);
						expression(6);
						}
						break;
					case 5:
						{
						_localctx = new EqualityExprContext(new ExpressionContext(_parentctx, _parentState));
						pushNewRecursionContext(_localctx, _startState, RULE_expression);
						setState(224);
						if (!(precpred(_ctx, 4))) throw new FailedPredicateException(this, "precpred(_ctx, 4)");
						setState(225);
						_la = _input.LA(1);
						if ( !(_la==EQEQ || _la==NEQ) ) {
						_errHandler.recoverInline(this);
						}
						else {
							if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
							_errHandler.reportMatch(this);
							consume();
						}
						setState(226);
						expression(5);
						}
						break;
					case 6:
						{
						_localctx = new LogicalAndExprContext(new ExpressionContext(_parentctx, _parentState));
						pushNewRecursionContext(_localctx, _startState, RULE_expression);
						setState(227);
						if (!(precpred(_ctx, 3))) throw new FailedPredicateException(this, "precpred(_ctx, 3)");
						setState(228);
						_la = _input.LA(1);
						if ( !(_la==AND || _la==AMPAMP) ) {
						_errHandler.recoverInline(this);
						}
						else {
							if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
							_errHandler.reportMatch(this);
							consume();
						}
						setState(229);
						expression(4);
						}
						break;
					case 7:
						{
						_localctx = new LogicalOrExprContext(new ExpressionContext(_parentctx, _parentState));
						pushNewRecursionContext(_localctx, _startState, RULE_expression);
						setState(230);
						if (!(precpred(_ctx, 2))) throw new FailedPredicateException(this, "precpred(_ctx, 2)");
						setState(231);
						_la = _input.LA(1);
						if ( !(_la==OR || _la==PIPEPIPE) ) {
						_errHandler.recoverInline(this);
						}
						else {
							if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
							_errHandler.reportMatch(this);
							consume();
						}
						setState(232);
						expression(3);
						}
						break;
					case 8:
						{
						_localctx = new MemberAccessExprContext(new ExpressionContext(_parentctx, _parentState));
						pushNewRecursionContext(_localctx, _startState, RULE_expression);
						setState(233);
						if (!(precpred(_ctx, 12))) throw new FailedPredicateException(this, "precpred(_ctx, 12)");
						setState(234);
						match(DOT);
						setState(235);
						match(IDENTIFIER);
						}
						break;
					case 9:
						{
						_localctx = new IndexAccessExprContext(new ExpressionContext(_parentctx, _parentState));
						pushNewRecursionContext(_localctx, _startState, RULE_expression);
						setState(236);
						if (!(precpred(_ctx, 11))) throw new FailedPredicateException(this, "precpred(_ctx, 11)");
						setState(237);
						match(LBRACK);
						setState(238);
						expression(0);
						setState(239);
						match(RBRACK);
						}
						break;
					}
					} 
				}
				setState(245);
				_errHandler.sync(this);
				_alt = getInterpreter().adaptivePredict(_input,22,_ctx);
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			unrollRecursionContexts(_parentctx);
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class PrimaryExpressionContext extends ParserRuleContext {
		public LiteralContext literal() {
			return getRuleContext(LiteralContext.class,0);
		}
		public TerminalNode IDENTIFIER() { return getToken(zincParser.IDENTIFIER, 0); }
		public PrimaryExpressionContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_primaryExpression; }
	}

	public final PrimaryExpressionContext primaryExpression() throws RecognitionException {
		PrimaryExpressionContext _localctx = new PrimaryExpressionContext(_ctx, getState());
		enterRule(_localctx, 40, RULE_primaryExpression);
		try {
			setState(248);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case TRUE:
			case FALSE:
			case NIL:
			case INTEGER:
			case FLOAT:
			case STRING:
				enterOuterAlt(_localctx, 1);
				{
				setState(246);
				literal();
				}
				break;
			case IDENTIFIER:
				enterOuterAlt(_localctx, 2);
				{
				setState(247);
				match(IDENTIFIER);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class LiteralContext extends ParserRuleContext {
		public TerminalNode INTEGER() { return getToken(zincParser.INTEGER, 0); }
		public TerminalNode FLOAT() { return getToken(zincParser.FLOAT, 0); }
		public TerminalNode STRING() { return getToken(zincParser.STRING, 0); }
		public BooleanLiteralContext booleanLiteral() {
			return getRuleContext(BooleanLiteralContext.class,0);
		}
		public TerminalNode NIL() { return getToken(zincParser.NIL, 0); }
		public LiteralContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_literal; }
	}

	public final LiteralContext literal() throws RecognitionException {
		LiteralContext _localctx = new LiteralContext(_ctx, getState());
		enterRule(_localctx, 42, RULE_literal);
		try {
			setState(255);
			_errHandler.sync(this);
			switch (_input.LA(1)) {
			case INTEGER:
				enterOuterAlt(_localctx, 1);
				{
				setState(250);
				match(INTEGER);
				}
				break;
			case FLOAT:
				enterOuterAlt(_localctx, 2);
				{
				setState(251);
				match(FLOAT);
				}
				break;
			case STRING:
				enterOuterAlt(_localctx, 3);
				{
				setState(252);
				match(STRING);
				}
				break;
			case TRUE:
			case FALSE:
				enterOuterAlt(_localctx, 4);
				{
				setState(253);
				booleanLiteral();
				}
				break;
			case NIL:
				enterOuterAlt(_localctx, 5);
				{
				setState(254);
				match(NIL);
				}
				break;
			default:
				throw new NoViableAltException(this);
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	@SuppressWarnings("CheckReturnValue")
	public static class BooleanLiteralContext extends ParserRuleContext {
		public TerminalNode TRUE() { return getToken(zincParser.TRUE, 0); }
		public TerminalNode FALSE() { return getToken(zincParser.FALSE, 0); }
		public BooleanLiteralContext(ParserRuleContext parent, int invokingState) {
			super(parent, invokingState);
		}
		@Override public int getRuleIndex() { return RULE_booleanLiteral; }
	}

	public final BooleanLiteralContext booleanLiteral() throws RecognitionException {
		BooleanLiteralContext _localctx = new BooleanLiteralContext(_ctx, getState());
		enterRule(_localctx, 44, RULE_booleanLiteral);
		int _la;
		try {
			enterOuterAlt(_localctx, 1);
			{
			setState(257);
			_la = _input.LA(1);
			if ( !(_la==TRUE || _la==FALSE) ) {
			_errHandler.recoverInline(this);
			}
			else {
				if ( _input.LA(1)==Token.EOF ) matchedEOF = true;
				_errHandler.reportMatch(this);
				consume();
			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			_errHandler.reportError(this, re);
			_errHandler.recover(this, re);
		}
		finally {
			exitRule();
		}
		return _localctx;
	}

	public boolean sempred(RuleContext _localctx, int ruleIndex, int predIndex) {
		switch (ruleIndex) {
		case 19:
			return expression_sempred((ExpressionContext)_localctx, predIndex);
		}
		return true;
	}
	private boolean expression_sempred(ExpressionContext _localctx, int predIndex) {
		switch (predIndex) {
		case 0:
			return precpred(_ctx, 8);
		case 1:
			return precpred(_ctx, 7);
		case 2:
			return precpred(_ctx, 6);
		case 3:
			return precpred(_ctx, 5);
		case 4:
			return precpred(_ctx, 4);
		case 5:
			return precpred(_ctx, 3);
		case 6:
			return precpred(_ctx, 2);
		case 7:
			return precpred(_ctx, 12);
		case 8:
			return precpred(_ctx, 11);
		}
		return true;
	}

	public static final String _serializedATN =
		"\u0004\u0001?\u0104\u0002\u0000\u0007\u0000\u0002\u0001\u0007\u0001\u0002"+
		"\u0002\u0007\u0002\u0002\u0003\u0007\u0003\u0002\u0004\u0007\u0004\u0002"+
		"\u0005\u0007\u0005\u0002\u0006\u0007\u0006\u0002\u0007\u0007\u0007\u0002"+
		"\b\u0007\b\u0002\t\u0007\t\u0002\n\u0007\n\u0002\u000b\u0007\u000b\u0002"+
		"\f\u0007\f\u0002\r\u0007\r\u0002\u000e\u0007\u000e\u0002\u000f\u0007\u000f"+
		"\u0002\u0010\u0007\u0010\u0002\u0011\u0007\u0011\u0002\u0012\u0007\u0012"+
		"\u0002\u0013\u0007\u0013\u0002\u0014\u0007\u0014\u0002\u0015\u0007\u0015"+
		"\u0002\u0016\u0007\u0016\u0001\u0000\u0005\u00000\b\u0000\n\u0000\f\u0000"+
		"3\t\u0000\u0001\u0000\u0001\u0000\u0001\u0001\u0001\u0001\u0003\u0001"+
		"9\b\u0001\u0001\u0002\u0001\u0002\u0001\u0002\u0001\u0002\u0003\u0002"+
		"?\b\u0002\u0001\u0002\u0001\u0002\u0001\u0002\u0001\u0003\u0001\u0003"+
		"\u0001\u0003\u0005\u0003G\b\u0003\n\u0003\f\u0003J\t\u0003\u0001\u0004"+
		"\u0001\u0004\u0001\u0004\u0003\u0004O\b\u0004\u0001\u0005\u0001\u0005"+
		"\u0001\u0005\u0001\u0005\u0001\u0005\u0003\u0005V\b\u0005\u0001\u0005"+
		"\u0001\u0005\u0001\u0005\u0001\u0005\u0001\u0005\u0001\u0005\u0003\u0005"+
		"^\b\u0005\u0001\u0005\u0001\u0005\u0001\u0005\u0003\u0005c\b\u0005\u0001"+
		"\u0006\u0001\u0006\u0001\u0006\u0005\u0006h\b\u0006\n\u0006\f\u0006k\t"+
		"\u0006\u0001\u0007\u0001\u0007\u0001\u0007\u0001\u0007\u0001\b\u0001\b"+
		"\u0001\t\u0001\t\u0001\n\u0001\n\u0001\n\u0001\n\u0001\n\u0001\n\u0005"+
		"\n{\b\n\n\n\f\n~\t\n\u0001\n\u0003\n\u0081\b\n\u0001\n\u0001\n\u0001\u000b"+
		"\u0001\u000b\u0001\u000b\u0001\u000b\u0003\u000b\u0089\b\u000b\u0001\f"+
		"\u0001\f\u0001\f\u0001\f\u0001\f\u0001\f\u0001\f\u0001\f\u0005\f\u0093"+
		"\b\f\n\f\f\f\u0096\t\f\u0001\f\u0001\f\u0001\f\u0001\f\u0001\f\u0001\f"+
		"\u0001\f\u0005\f\u009f\b\f\n\f\f\f\u00a2\t\f\u0001\f\u0003\f\u00a5\b\f"+
		"\u0001\f\u0001\f\u0003\f\u00a9\b\f\u0001\r\u0001\r\u0001\r\u0001\r\u0001"+
		"\r\u0001\r\u0003\r\u00b1\b\r\u0001\u000e\u0001\u000e\u0001\u000e\u0003"+
		"\u000e\u00b6\b\u000e\u0001\u000f\u0001\u000f\u0003\u000f\u00ba\b\u000f"+
		"\u0001\u0010\u0001\u0010\u0001\u0011\u0001\u0011\u0001\u0012\u0001\u0012"+
		"\u0005\u0012\u00c2\b\u0012\n\u0012\f\u0012\u00c5\t\u0012\u0001\u0012\u0001"+
		"\u0012\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001"+
		"\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0003\u0013\u00d3"+
		"\b\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001"+
		"\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001"+
		"\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001"+
		"\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001"+
		"\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0001\u0013\u0005"+
		"\u0013\u00f2\b\u0013\n\u0013\f\u0013\u00f5\t\u0013\u0001\u0014\u0001\u0014"+
		"\u0003\u0014\u00f9\b\u0014\u0001\u0015\u0001\u0015\u0001\u0015\u0001\u0015"+
		"\u0001\u0015\u0003\u0015\u0100\b\u0015\u0001\u0016\u0001\u0016\u0001\u0016"+
		"\u0000\u0001&\u0017\u0000\u0002\u0004\u0006\b\n\f\u000e\u0010\u0012\u0014"+
		"\u0016\u0018\u001a\u001c\u001e \"$&(*,\u0000\t\u0003\u0000\u0015\u0015"+
		"\u001e\u001e++\u0001\u0000\u001f!\u0001\u0000\u001d\u001e\u0001\u0000"+
		",-\u0001\u0000%(\u0001\u0000#$\u0002\u0000\u0013\u0013))\u0002\u0000\u0014"+
		"\u0014**\u0001\u0000\u0010\u0011\u0116\u00001\u0001\u0000\u0000\u0000"+
		"\u00028\u0001\u0000\u0000\u0000\u0004:\u0001\u0000\u0000\u0000\u0006C"+
		"\u0001\u0000\u0000\u0000\bK\u0001\u0000\u0000\u0000\nb\u0001\u0000\u0000"+
		"\u0000\fd\u0001\u0000\u0000\u0000\u000el\u0001\u0000\u0000\u0000\u0010"+
		"p\u0001\u0000\u0000\u0000\u0012r\u0001\u0000\u0000\u0000\u0014t\u0001"+
		"\u0000\u0000\u0000\u0016\u0084\u0001\u0000\u0000\u0000\u0018\u00a8\u0001"+
		"\u0000\u0000\u0000\u001a\u00b0\u0001\u0000\u0000\u0000\u001c\u00b2\u0001"+
		"\u0000\u0000\u0000\u001e\u00b7\u0001\u0000\u0000\u0000 \u00bb\u0001\u0000"+
		"\u0000\u0000\"\u00bd\u0001\u0000\u0000\u0000$\u00bf\u0001\u0000\u0000"+
		"\u0000&\u00d2\u0001\u0000\u0000\u0000(\u00f8\u0001\u0000\u0000\u0000*"+
		"\u00ff\u0001\u0000\u0000\u0000,\u0101\u0001\u0000\u0000\u0000.0\u0003"+
		"\u0002\u0001\u0000/.\u0001\u0000\u0000\u000003\u0001\u0000\u0000\u0000"+
		"1/\u0001\u0000\u0000\u000012\u0001\u0000\u0000\u000024\u0001\u0000\u0000"+
		"\u000031\u0001\u0000\u0000\u000045\u0005\u0000\u0000\u00015\u0001\u0001"+
		"\u0000\u0000\u000069\u0003\u0004\u0002\u000079\u0003\u000e\u0007\u0000"+
		"86\u0001\u0000\u0000\u000087\u0001\u0000\u0000\u00009\u0003\u0001\u0000"+
		"\u0000\u0000:;\u0005\u0003\u0000\u0000;<\u0005\u001c\u0000\u0000<>\u0005"+
		"5\u0000\u0000=?\u0003\u0006\u0003\u0000>=\u0001\u0000\u0000\u0000>?\u0001"+
		"\u0000\u0000\u0000?@\u0001\u0000\u0000\u0000@A\u00056\u0000\u0000AB\u0003"+
		"$\u0012\u0000B\u0005\u0001\u0000\u0000\u0000CH\u0003\b\u0004\u0000DE\u0005"+
		"2\u0000\u0000EG\u0003\b\u0004\u0000FD\u0001\u0000\u0000\u0000GJ\u0001"+
		"\u0000\u0000\u0000HF\u0001\u0000\u0000\u0000HI\u0001\u0000\u0000\u0000"+
		"I\u0007\u0001\u0000\u0000\u0000JH\u0001\u0000\u0000\u0000KN\u0005\u001c"+
		"\u0000\u0000LM\u00053\u0000\u0000MO\u0003\n\u0005\u0000NL\u0001\u0000"+
		"\u0000\u0000NO\u0001\u0000\u0000\u0000O\t\u0001\u0000\u0000\u0000PU\u0005"+
		"\u001c\u0000\u0000QR\u0005%\u0000\u0000RS\u0003\f\u0006\u0000ST\u0005"+
		"\'\u0000\u0000TV\u0001\u0000\u0000\u0000UQ\u0001\u0000\u0000\u0000UV\u0001"+
		"\u0000\u0000\u0000Vc\u0001\u0000\u0000\u0000WX\u00059\u0000\u0000XY\u0003"+
		"\n\u0005\u0000YZ\u0005:\u0000\u0000Zc\u0001\u0000\u0000\u0000[]\u0005"+
		"5\u0000\u0000\\^\u0003\f\u0006\u0000]\\\u0001\u0000\u0000\u0000]^\u0001"+
		"\u0000\u0000\u0000^_\u0001\u0000\u0000\u0000_`\u00056\u0000\u0000`a\u0005"+
		"/\u0000\u0000ac\u0003\n\u0005\u0000bP\u0001\u0000\u0000\u0000bW\u0001"+
		"\u0000\u0000\u0000b[\u0001\u0000\u0000\u0000c\u000b\u0001\u0000\u0000"+
		"\u0000di\u0003\n\u0005\u0000ef\u00052\u0000\u0000fh\u0003\n\u0005\u0000"+
		"ge\u0001\u0000\u0000\u0000hk\u0001\u0000\u0000\u0000ig\u0001\u0000\u0000"+
		"\u0000ij\u0001\u0000\u0000\u0000j\r\u0001\u0000\u0000\u0000ki\u0001\u0000"+
		"\u0000\u0000lm\u0003\u0010\b\u0000mn\u0005\"\u0000\u0000no\u0003&\u0013"+
		"\u0000o\u000f\u0001\u0000\u0000\u0000pq\u0005\u001c\u0000\u0000q\u0011"+
		"\u0001\u0000\u0000\u0000rs\u0003&\u0013\u0000s\u0013\u0001\u0000\u0000"+
		"\u0000tu\u0005\f\u0000\u0000uv\u0003&\u0013\u0000vw\u00057\u0000\u0000"+
		"w|\u0003\u0016\u000b\u0000xy\u00052\u0000\u0000y{\u0003\u0016\u000b\u0000"+
		"zx\u0001\u0000\u0000\u0000{~\u0001\u0000\u0000\u0000|z\u0001\u0000\u0000"+
		"\u0000|}\u0001\u0000\u0000\u0000}\u0080\u0001\u0000\u0000\u0000~|\u0001"+
		"\u0000\u0000\u0000\u007f\u0081\u00052\u0000\u0000\u0080\u007f\u0001\u0000"+
		"\u0000\u0000\u0080\u0081\u0001\u0000\u0000\u0000\u0081\u0082\u0001\u0000"+
		"\u0000\u0000\u0082\u0083\u00058\u0000\u0000\u0083\u0015\u0001\u0000\u0000"+
		"\u0000\u0084\u0085\u0003\u0018\f\u0000\u0085\u0088\u0005.\u0000\u0000"+
		"\u0086\u0089\u0003$\u0012\u0000\u0087\u0089\u0003&\u0013\u0000\u0088\u0086"+
		"\u0001\u0000\u0000\u0000\u0088\u0087\u0001\u0000\u0000\u0000\u0089\u0017"+
		"\u0001\u0000\u0000\u0000\u008a\u00a9\u0005<\u0000\u0000\u008b\u00a9\u0003"+
		"*\u0015\u0000\u008c\u00a9\u0005\u001c\u0000\u0000\u008d\u00a9\u0003\u001a"+
		"\r\u0000\u008e\u008f\u00055\u0000\u0000\u008f\u0094\u0003\u0018\f\u0000"+
		"\u0090\u0091\u00052\u0000\u0000\u0091\u0093\u0003\u0018\f\u0000\u0092"+
		"\u0090\u0001\u0000\u0000\u0000\u0093\u0096\u0001\u0000\u0000\u0000\u0094"+
		"\u0092\u0001\u0000\u0000\u0000\u0094\u0095\u0001\u0000\u0000\u0000\u0095"+
		"\u0097\u0001\u0000\u0000\u0000\u0096\u0094\u0001\u0000\u0000\u0000\u0097"+
		"\u0098\u00056\u0000\u0000\u0098\u00a9\u0001\u0000\u0000\u0000\u0099\u009a"+
		"\u0005\u001c\u0000\u0000\u009a\u009b\u00057\u0000\u0000\u009b\u00a0\u0003"+
		"\u001c\u000e\u0000\u009c\u009d\u00052\u0000\u0000\u009d\u009f\u0003\u001c"+
		"\u000e\u0000\u009e\u009c\u0001\u0000\u0000\u0000\u009f\u00a2\u0001\u0000"+
		"\u0000\u0000\u00a0\u009e\u0001\u0000\u0000\u0000\u00a0\u00a1\u0001\u0000"+
		"\u0000\u0000\u00a1\u00a4\u0001\u0000\u0000\u0000\u00a2\u00a0\u0001\u0000"+
		"\u0000\u0000\u00a3\u00a5\u00052\u0000\u0000\u00a4\u00a3\u0001\u0000\u0000"+
		"\u0000\u00a4\u00a5\u0001\u0000\u0000\u0000\u00a5\u00a6\u0001\u0000\u0000"+
		"\u0000\u00a6\u00a7\u00058\u0000\u0000\u00a7\u00a9\u0001\u0000\u0000\u0000"+
		"\u00a8\u008a\u0001\u0000\u0000\u0000\u00a8\u008b\u0001\u0000\u0000\u0000"+
		"\u00a8\u008c\u0001\u0000\u0000\u0000\u00a8\u008d\u0001\u0000\u0000\u0000"+
		"\u00a8\u008e\u0001\u0000\u0000\u0000\u00a8\u0099\u0001\u0000\u0000\u0000"+
		"\u00a9\u0019\u0001\u0000\u0000\u0000\u00aa\u00ab\u0005\u0019\u0000\u0000"+
		"\u00ab\u00ac\u0005,\u0000\u0000\u00ac\u00b1\u0005\u0019\u0000\u0000\u00ad"+
		"\u00ae\u0005\u0019\u0000\u0000\u00ae\u00af\u0005-\u0000\u0000\u00af\u00b1"+
		"\u0005\u0019\u0000\u0000\u00b0\u00aa\u0001\u0000\u0000\u0000\u00b0\u00ad"+
		"\u0001\u0000\u0000\u0000\u00b1\u001b\u0001\u0000\u0000\u0000\u00b2\u00b5"+
		"\u0005\u001c\u0000\u0000\u00b3\u00b4\u00053\u0000\u0000\u00b4\u00b6\u0003"+
		"\u0018\f\u0000\u00b5\u00b3\u0001\u0000\u0000\u0000\u00b5\u00b6\u0001\u0000"+
		"\u0000\u0000\u00b6\u001d\u0001\u0000\u0000\u0000\u00b7\u00b9\u0005\r\u0000"+
		"\u0000\u00b8\u00ba\u0003&\u0013\u0000\u00b9\u00b8\u0001\u0000\u0000\u0000"+
		"\u00b9\u00ba\u0001\u0000\u0000\u0000\u00ba\u001f\u0001\u0000\u0000\u0000"+
		"\u00bb\u00bc\u0005\u000e\u0000\u0000\u00bc!\u0001\u0000\u0000\u0000\u00bd"+
		"\u00be\u0005\u000f\u0000\u0000\u00be#\u0001\u0000\u0000\u0000\u00bf\u00c3"+
		"\u00057\u0000\u0000\u00c0\u00c2\u0003\u0002\u0001\u0000\u00c1\u00c0\u0001"+
		"\u0000\u0000\u0000\u00c2\u00c5\u0001\u0000\u0000\u0000\u00c3\u00c1\u0001"+
		"\u0000\u0000\u0000\u00c3\u00c4\u0001\u0000\u0000\u0000\u00c4\u00c6\u0001"+
		"\u0000\u0000\u0000\u00c5\u00c3\u0001\u0000\u0000\u0000\u00c6\u00c7\u0005"+
		"8\u0000\u0000\u00c7%\u0001\u0000\u0000\u0000\u00c8\u00c9\u0006\u0013\uffff"+
		"\uffff\u0000\u00c9\u00d3\u0003(\u0014\u0000\u00ca\u00cb\u0005\u0005\u0000"+
		"\u0000\u00cb\u00d3\u0003&\u0013\n\u00cc\u00cd\u0007\u0000\u0000\u0000"+
		"\u00cd\u00d3\u0003&\u0013\t\u00ce\u00cf\u00055\u0000\u0000\u00cf\u00d0"+
		"\u0003&\u0013\u0000\u00d0\u00d1\u00056\u0000\u0000\u00d1\u00d3\u0001\u0000"+
		"\u0000\u0000\u00d2\u00c8\u0001\u0000\u0000\u0000\u00d2\u00ca\u0001\u0000"+
		"\u0000\u0000\u00d2\u00cc\u0001\u0000\u0000\u0000\u00d2\u00ce\u0001\u0000"+
		"\u0000\u0000\u00d3\u00f3\u0001\u0000\u0000\u0000\u00d4\u00d5\n\b\u0000"+
		"\u0000\u00d5\u00d6\u0007\u0001\u0000\u0000\u00d6\u00f2\u0003&\u0013\t"+
		"\u00d7\u00d8\n\u0007\u0000\u0000\u00d8\u00d9\u0007\u0002\u0000\u0000\u00d9"+
		"\u00f2\u0003&\u0013\b\u00da\u00db\n\u0006\u0000\u0000\u00db\u00dc\u0007"+
		"\u0003\u0000\u0000\u00dc\u00f2\u0003&\u0013\u0007\u00dd\u00de\n\u0005"+
		"\u0000\u0000\u00de\u00df\u0007\u0004\u0000\u0000\u00df\u00f2\u0003&\u0013"+
		"\u0006\u00e0\u00e1\n\u0004\u0000\u0000\u00e1\u00e2\u0007\u0005\u0000\u0000"+
		"\u00e2\u00f2\u0003&\u0013\u0005\u00e3\u00e4\n\u0003\u0000\u0000\u00e4"+
		"\u00e5\u0007\u0006\u0000\u0000\u00e5\u00f2\u0003&\u0013\u0004\u00e6\u00e7"+
		"\n\u0002\u0000\u0000\u00e7\u00e8\u0007\u0007\u0000\u0000\u00e8\u00f2\u0003"+
		"&\u0013\u0003\u00e9\u00ea\n\f\u0000\u0000\u00ea\u00eb\u00051\u0000\u0000"+
		"\u00eb\u00f2\u0005\u001c\u0000\u0000\u00ec\u00ed\n\u000b\u0000\u0000\u00ed"+
		"\u00ee\u00059\u0000\u0000\u00ee\u00ef\u0003&\u0013\u0000\u00ef\u00f0\u0005"+
		":\u0000\u0000\u00f0\u00f2\u0001\u0000\u0000\u0000\u00f1\u00d4\u0001\u0000"+
		"\u0000\u0000\u00f1\u00d7\u0001\u0000\u0000\u0000\u00f1\u00da\u0001\u0000"+
		"\u0000\u0000\u00f1\u00dd\u0001\u0000\u0000\u0000\u00f1\u00e0\u0001\u0000"+
		"\u0000\u0000\u00f1\u00e3\u0001\u0000\u0000\u0000\u00f1\u00e6\u0001\u0000"+
		"\u0000\u0000\u00f1\u00e9\u0001\u0000\u0000\u0000\u00f1\u00ec\u0001\u0000"+
		"\u0000\u0000\u00f2\u00f5\u0001\u0000\u0000\u0000\u00f3\u00f1\u0001\u0000"+
		"\u0000\u0000\u00f3\u00f4\u0001\u0000\u0000\u0000\u00f4\'\u0001\u0000\u0000"+
		"\u0000\u00f5\u00f3\u0001\u0000\u0000\u0000\u00f6\u00f9\u0003*\u0015\u0000"+
		"\u00f7\u00f9\u0005\u001c\u0000\u0000\u00f8\u00f6\u0001\u0000\u0000\u0000"+
		"\u00f8\u00f7\u0001\u0000\u0000\u0000\u00f9)\u0001\u0000\u0000\u0000\u00fa"+
		"\u0100\u0005\u0019\u0000\u0000\u00fb\u0100\u0005\u001a\u0000\u0000\u00fc"+
		"\u0100\u0005\u001b\u0000\u0000\u00fd\u0100\u0003,\u0016\u0000\u00fe\u0100"+
		"\u0005\u0012\u0000\u0000\u00ff\u00fa\u0001\u0000\u0000\u0000\u00ff\u00fb"+
		"\u0001\u0000\u0000\u0000\u00ff\u00fc\u0001\u0000\u0000\u0000\u00ff\u00fd"+
		"\u0001\u0000\u0000\u0000\u00ff\u00fe\u0001\u0000\u0000\u0000\u0100+\u0001"+
		"\u0000\u0000\u0000\u0101\u0102\u0007\b\u0000\u0000\u0102-\u0001\u0000"+
		"\u0000\u0000\u001918>HNU]bi|\u0080\u0088\u0094\u00a0\u00a4\u00a8\u00b0"+
		"\u00b5\u00b9\u00c3\u00d2\u00f1\u00f3\u00f8\u00ff";
	public static final ATN _ATN =
		new ATNDeserializer().deserialize(_serializedATN.toCharArray());
	static {
		_decisionToDFA = new DFA[_ATN.getNumberOfDecisions()];
		for (int i = 0; i < _ATN.getNumberOfDecisions(); i++) {
			_decisionToDFA[i] = new DFA(_ATN.getDecisionState(i), i);
		}
	}
}