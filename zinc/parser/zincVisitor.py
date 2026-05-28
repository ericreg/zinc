# Generated from zinc.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .zincParser import zincParser
else:
    from zincParser import zincParser

# This class defines a complete generic visitor for a parse tree produced by zincParser.

class zincVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by zincParser#program.
    def visitProgram(self, ctx:zincParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#statement.
    def visitStatement(self, ctx:zincParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#importStatement.
    def visitImportStatement(self, ctx:zincParser.ImportStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#importPath.
    def visitImportPath(self, ctx:zincParser.ImportPathContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#importNameList.
    def visitImportNameList(self, ctx:zincParser.ImportNameListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#qualifiedName.
    def visitQualifiedName(self, ctx:zincParser.QualifiedNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#constDeclaration.
    def visitConstDeclaration(self, ctx:zincParser.ConstDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#structDeclaration.
    def visitStructDeclaration(self, ctx:zincParser.StructDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#enumDeclaration.
    def visitEnumDeclaration(self, ctx:zincParser.EnumDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#attributeBlock.
    def visitAttributeBlock(self, ctx:zincParser.AttributeBlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#structComposition.
    def visitStructComposition(self, ctx:zincParser.StructCompositionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#orthogonalComposition.
    def visitOrthogonalComposition(self, ctx:zincParser.OrthogonalCompositionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#mergeComposition.
    def visitMergeComposition(self, ctx:zincParser.MergeCompositionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#structBody.
    def visitStructBody(self, ctx:zincParser.StructBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#structMember.
    def visitStructMember(self, ctx:zincParser.StructMemberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#structField.
    def visitStructField(self, ctx:zincParser.StructFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#enumBody.
    def visitEnumBody(self, ctx:zincParser.EnumBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#enumVariant.
    def visitEnumVariant(self, ctx:zincParser.EnumVariantContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#enumVariantFieldType.
    def visitEnumVariantFieldType(self, ctx:zincParser.EnumVariantFieldTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#functionDeclaration.
    def visitFunctionDeclaration(self, ctx:zincParser.FunctionDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#asyncFunctionDeclaration.
    def visitAsyncFunctionDeclaration(self, ctx:zincParser.AsyncFunctionDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#parameterList.
    def visitParameterList(self, ctx:zincParser.ParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#parameter.
    def visitParameter(self, ctx:zincParser.ParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#typeAlternative.
    def visitTypeAlternative(self, ctx:zincParser.TypeAlternativeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#type.
    def visitType(self, ctx:zincParser.TypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#typeList.
    def visitTypeList(self, ctx:zincParser.TypeListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#tupleType.
    def visitTupleType(self, ctx:zincParser.TupleTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#typedVariableAssignment.
    def visitTypedVariableAssignment(self, ctx:zincParser.TypedVariableAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#typedAssignmentTarget.
    def visitTypedAssignmentTarget(self, ctx:zincParser.TypedAssignmentTargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#variableAssignment.
    def visitVariableAssignment(self, ctx:zincParser.VariableAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#assignmentOperator.
    def visitAssignmentOperator(self, ctx:zincParser.AssignmentOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#outAssignment.
    def visitOutAssignment(self, ctx:zincParser.OutAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#assignmentTarget.
    def visitAssignmentTarget(self, ctx:zincParser.AssignmentTargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#tupleAssignmentTarget.
    def visitTupleAssignmentTarget(self, ctx:zincParser.TupleAssignmentTargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#expressionStatement.
    def visitExpressionStatement(self, ctx:zincParser.ExpressionStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#ifStatement.
    def visitIfStatement(self, ctx:zincParser.IfStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#forStatement.
    def visitForStatement(self, ctx:zincParser.ForStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#forBinding.
    def visitForBinding(self, ctx:zincParser.ForBindingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#whileStatement.
    def visitWhileStatement(self, ctx:zincParser.WhileStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#loopStatement.
    def visitLoopStatement(self, ctx:zincParser.LoopStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#matchStatement.
    def visitMatchStatement(self, ctx:zincParser.MatchStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#matchArm.
    def visitMatchArm(self, ctx:zincParser.MatchArmContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#pattern.
    def visitPattern(self, ctx:zincParser.PatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#resultOptionPattern.
    def visitResultOptionPattern(self, ctx:zincParser.ResultOptionPatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#enumVariantPattern.
    def visitEnumVariantPattern(self, ctx:zincParser.EnumVariantPatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#rangePattern.
    def visitRangePattern(self, ctx:zincParser.RangePatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#enumVariantPath.
    def visitEnumVariantPath(self, ctx:zincParser.EnumVariantPathContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#enumVariantFieldPattern.
    def visitEnumVariantFieldPattern(self, ctx:zincParser.EnumVariantFieldPatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#fieldPattern.
    def visitFieldPattern(self, ctx:zincParser.FieldPatternContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#returnStatement.
    def visitReturnStatement(self, ctx:zincParser.ReturnStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#failStatement.
    def visitFailStatement(self, ctx:zincParser.FailStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#breakStatement.
    def visitBreakStatement(self, ctx:zincParser.BreakStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#continueStatement.
    def visitContinueStatement(self, ctx:zincParser.ContinueStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#spawnStatement.
    def visitSpawnStatement(self, ctx:zincParser.SpawnStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#selectStatement.
    def visitSelectStatement(self, ctx:zincParser.SelectStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#channelSendStatement.
    def visitChannelSendStatement(self, ctx:zincParser.ChannelSendStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#block.
    def visitBlock(self, ctx:zincParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#membershipExpr.
    def visitMembershipExpr(self, ctx:zincParser.MembershipExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#powerExpr.
    def visitPowerExpr(self, ctx:zincParser.PowerExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#bitwiseOrExpr.
    def visitBitwiseOrExpr(self, ctx:zincParser.BitwiseOrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#bitwiseAndExpr.
    def visitBitwiseAndExpr(self, ctx:zincParser.BitwiseAndExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#additiveExpr.
    def visitAdditiveExpr(self, ctx:zincParser.AdditiveExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#parenExpr.
    def visitParenExpr(self, ctx:zincParser.ParenExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#unaryExpr.
    def visitUnaryExpr(self, ctx:zincParser.UnaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#primaryExpr.
    def visitPrimaryExpr(self, ctx:zincParser.PrimaryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#lambdaExpr.
    def visitLambdaExpr(self, ctx:zincParser.LambdaExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#indexAccessExpr.
    def visitIndexAccessExpr(self, ctx:zincParser.IndexAccessExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#functionCallExpr.
    def visitFunctionCallExpr(self, ctx:zincParser.FunctionCallExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#ifExpr.
    def visitIfExpr(self, ctx:zincParser.IfExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#channelReceiveExpr.
    def visitChannelReceiveExpr(self, ctx:zincParser.ChannelReceiveExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#memberAccessExpr.
    def visitMemberAccessExpr(self, ctx:zincParser.MemberAccessExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#blockExpr.
    def visitBlockExpr(self, ctx:zincParser.BlockExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#bitwiseXorExpr.
    def visitBitwiseXorExpr(self, ctx:zincParser.BitwiseXorExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#logicalAndExpr.
    def visitLogicalAndExpr(self, ctx:zincParser.LogicalAndExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#awaitExpr.
    def visitAwaitExpr(self, ctx:zincParser.AwaitExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#relationalExpr.
    def visitRelationalExpr(self, ctx:zincParser.RelationalExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#shiftExpr.
    def visitShiftExpr(self, ctx:zincParser.ShiftExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#logicalOrExpr.
    def visitLogicalOrExpr(self, ctx:zincParser.LogicalOrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#tryExpr.
    def visitTryExpr(self, ctx:zincParser.TryExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#multiplicativeExpr.
    def visitMultiplicativeExpr(self, ctx:zincParser.MultiplicativeExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#rangeExpr.
    def visitRangeExpr(self, ctx:zincParser.RangeExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#equalityExpr.
    def visitEqualityExpr(self, ctx:zincParser.EqualityExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#ifExpression.
    def visitIfExpression(self, ctx:zincParser.IfExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#tryExpression.
    def visitTryExpression(self, ctx:zincParser.TryExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#blockExpression.
    def visitBlockExpression(self, ctx:zincParser.BlockExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#primaryExpression.
    def visitPrimaryExpression(self, ctx:zincParser.PrimaryExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#builtinTypeQuery.
    def visitBuiltinTypeQuery(self, ctx:zincParser.BuiltinTypeQueryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#typeQueryType.
    def visitTypeQueryType(self, ctx:zincParser.TypeQueryTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#builtinResultOptionConstructor.
    def visitBuiltinResultOptionConstructor(self, ctx:zincParser.BuiltinResultOptionConstructorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#memberAccess.
    def visitMemberAccess(self, ctx:zincParser.MemberAccessContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#indexAccess.
    def visitIndexAccess(self, ctx:zincParser.IndexAccessContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#literal.
    def visitLiteral(self, ctx:zincParser.LiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#unitLiteral.
    def visitUnitLiteral(self, ctx:zincParser.UnitLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#booleanLiteral.
    def visitBooleanLiteral(self, ctx:zincParser.BooleanLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#arrayLiteral.
    def visitArrayLiteral(self, ctx:zincParser.ArrayLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#tupleLiteral.
    def visitTupleLiteral(self, ctx:zincParser.TupleLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#collectionLiteral.
    def visitCollectionLiteral(self, ctx:zincParser.CollectionLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#anonymousStructType.
    def visitAnonymousStructType(self, ctx:zincParser.AnonymousStructTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#anonymousStructFieldType.
    def visitAnonymousStructFieldType(self, ctx:zincParser.AnonymousStructFieldTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#anonymousStructLiteral.
    def visitAnonymousStructLiteral(self, ctx:zincParser.AnonymousStructLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#dictEntry.
    def visitDictEntry(self, ctx:zincParser.DictEntryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#structInstantiation.
    def visitStructInstantiation(self, ctx:zincParser.StructInstantiationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#enumVariantConstruction.
    def visitEnumVariantConstruction(self, ctx:zincParser.EnumVariantConstructionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#fieldInit.
    def visitFieldInit(self, ctx:zincParser.FieldInitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#structFieldEntry.
    def visitStructFieldEntry(self, ctx:zincParser.StructFieldEntryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#fieldSpread.
    def visitFieldSpread(self, ctx:zincParser.FieldSpreadContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#argumentList.
    def visitArgumentList(self, ctx:zincParser.ArgumentListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#argument.
    def visitArgument(self, ctx:zincParser.ArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#selectReceiveCase.
    def visitSelectReceiveCase(self, ctx:zincParser.SelectReceiveCaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#selectSendCase.
    def visitSelectSendCase(self, ctx:zincParser.SelectSendCaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#selectDefaultCase.
    def visitSelectDefaultCase(self, ctx:zincParser.SelectDefaultCaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#selectReceiveBinding.
    def visitSelectReceiveBinding(self, ctx:zincParser.SelectReceiveBindingContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by zincParser#lambdaExpression.
    def visitLambdaExpression(self, ctx:zincParser.LambdaExpressionContext):
        return self.visitChildren(ctx)



del zincParser