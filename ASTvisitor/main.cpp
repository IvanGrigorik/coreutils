#include "clang/AST/AST.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include "clang/ASTMatchers/ASTMatchers.h"
#include "clang/Frontend/ASTConsumers.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendActions.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/Tooling.h"

#include <iostream>
#include <map>
#include <set>

using namespace clang;
using namespace clang::tooling;
using namespace llvm;
using namespace clang::ast_matchers;

static llvm::cl::OptionCategory ToolCategory("getopt-type-extractor");

class OptargVisitor : public RecursiveASTVisitor<OptargVisitor> {
private:
  // Local "static" variables to keep track of case statements and conversion
  // functions
  std::vector<char> currentCases{};
  std::map<std::string, std::string> FuncTypeMap;
  std::vector<std::unique_ptr<ASTUnit>> &ASTUnits;

  // Context, needed for AST visitor
  ASTContext *Context;

public:
  explicit OptargVisitor(std::vector<std::unique_ptr<ASTUnit>> &ASTUnits)
      : ASTUnits(ASTUnits) {

    initTypeMap();
  }

  // Main visitor entry point
  void analyzeAll() {
    for (const auto &AST : ASTUnits) {
      Context = &AST->getASTContext();
      TraverseDecl(Context->getTranslationUnitDecl());
    }
  }

  bool VisitCaseStmt(CaseStmt *S) {
    Expr *E = S->getLHS();
    // llvm::outs() << E << '\n';

    llvm::SmallString<16> Buffer;

    clang::Expr::EvalResult R;
    if (E->EvaluateAsInt(R, *Context)) {
      // uint64_t C = R.Val.getInt();
      int val_int = R.Val.getInt().getSExtValue();
      if (val_int < 0) {
        return true;
      }
      char val = static_cast<char>(val_int);
      this->currentCases.push_back(val);
    }

    return true;
  }

  bool VisitBreakStmt(BreakStmt *S) {
    // for (auto& cs : this->currentCases) {
    //   llvm::outs() << cs << '\n';
    // }
    currentCases.clear();
    // llvm::outs() << "Break encountered!\n";
    return true;
  }

  //* functions visitor
  bool VisitCallExpr(CallExpr *call) {
    auto *callee = call->getDirectCallee();
    if (!callee) {
      return true;
    }

    StringRef name = callee->getName();
    if (call->getNumArgs() <= 0) {
      return true;
    }

    // Main code of the function visitor (invoked only in one of the function
    // argument is optarg)
    Expr *arg = call->getArg(0)->IgnoreParenImpCasts();
    if (DeclRefExpr *dre = dyn_cast<DeclRefExpr>(arg)) {

      if (dre->getNameInfo().getAsString() == "optarg") {

        // Gather all cases which converts optarg like that
        llvm::outs() << "shared cases: ";
        for (auto &sharedCase_ch : this->currentCases) {
          llvm::outs() << sharedCase_ch << " ";
        }
        llvm::outs() << '\n';
        // Truncate two last chars
        // cases = cases.substr(0, cases.size() - 2);

        // Gather types
        std::string types = inferTypeRecursive(name, {});

        llvm::outs() << "optarg used in function: " << name << "\n";
        llvm::outs() << "Inferred type: " << types << "\n";
      }
    }
    return true;
  }

  // Map of function-to-type conversions
private:
  void initTypeMap() {
    FuncTypeMap = {
        {"atoi", "int"},
        {"atol", "long"},
        {"atoll", "long long"},
        {"to_uchar", "unsigned char"},
        {"strdup", "char *"},
        {"strndup", "char *"},
        {"strcpy", "char *"},
        {"strncpy", "char *"},
        {"strcat", "char *"},
        {"strncat", "char *"},
        {"quote", "char *"},
        {"parse_user_spec_warn", "char *"},
        {"strtol", "long"},
        {"strtoul", "unsigned long"},
        {"strtoll", "long long"},
        {"strtoull", "unsigned long long"},
        {"sscanf", "mixed"},
        {"memcpy", "raw"},
        {"sprintf", "formatted string"},
        {"snprintf", "formatted string"},
        {"strlen", "char *"},
        {"xnumtoumax", "unsigned long"},
        {"xstrtod", "double"},
        {"xstrtold", "long double"},
        {"xstrtol", "long"},
        {"xstrtoul", "unsigned long"},
        {"xstrtoll", "long long"},
        {"xstrtoull", "unsigned long long"},
        {"xstrtoimax", "long"},
        {"xstrtoumax", "unsigned long"},
    };
  }

  // Trying to deduce type recursively
  std::string inferTypeRecursive(StringRef funcName,
                                 std::set<std::string> visited) {
    std::string fname = funcName.str();
    if (FuncTypeMap.count(fname)) {
      return FuncTypeMap[fname];
    }
    if (visited.count(fname)) {
      return "unknown";
    }
    visited.insert(fname);

    for (const auto &AST : ASTUnits) {
      TranslationUnitDecl *tu = AST->getASTContext().getTranslationUnitDecl();
      for (auto *decl : tu->decls()) {
        FunctionDecl *fd = dyn_cast<FunctionDecl>(decl);
        if (!fd || !(fd->getNameAsString() == fname && fd->hasBody())) {
          continue;
        }

        // Trying to gather the types from functions
        std::set<std::string> resultTypes =
            gatherTypesFromStmt(fd->getBody(), visited);

        if (resultTypes.empty()) {
          continue;
        }

        // The set have only one element - return it!
        if (resultTypes.size() < 2) {
          return *std::next(resultTypes.begin(), 1);
        }

        // return the potential types (if there are branching instructions)
        std::string combined = "potential: ";
        for (const std::string &t : resultTypes) {
          combined += t + ", ";
        }
        combined = combined.substr(0, combined.size() - 2);

        return combined;
      }
    }
    return "unknown";
  }

  std::set<std::string> gatherTypesFromStmt(Stmt *stmt,
                                            std::set<std::string> &visited) {
    std::set<std::string> types;
    if (!stmt) {
      return types;
    }

    for (Stmt *child : stmt->children()) {
      if (!child)
        continue;

      // If we encountered another function call - trying to parse this
      // function call as well
      if (CallExpr *call = dyn_cast<CallExpr>(child)) {
        if (FunctionDecl *fd = call->getDirectCallee()) {
          std::string name = fd->getNameAsString();
          types.insert(inferTypeRecursive(name, visited));
        }
      } else {
        std::set<std::string> childTypes = gatherTypesFromStmt(child, visited);
        types.insert(childTypes.begin(), childTypes.end());
      }
    }
    return types;
  }
};

int main(int argc, const char **argv) {
  // Standard clang parsing
  auto ExpectedParser = CommonOptionsParser::create(argc, argv, ToolCategory);
  if (!ExpectedParser) {
    llvm::errs() << ExpectedParser.takeError();
    return 1;
  }
  CommonOptionsParser &OptionsParser = ExpectedParser.get();

  // Trying to builds ASTs
  ClangTool Tool(OptionsParser.getCompilations(),
                 OptionsParser.getSourcePathList());
  std::vector<std::unique_ptr<ASTUnit>> ASTs;
  if (Tool.buildASTs(ASTs) != 0) {
    llvm::errs() << "Failed to build ASTs\n";
    return 1;
  }

  // Visit all of the ASTs
  OptargVisitor visitor(ASTs);
  visitor.analyzeAll();

  return 0;
}
