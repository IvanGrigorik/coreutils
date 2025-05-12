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
  std::vector<std::string> currentCases{};
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

    llvm::SmallString<16> Buffer;
    clang::Expr::EvalResult R;

    if (E->EvaluateAsInt(R, *Context)) {
      int val_int = R.Val.getInt().getSExtValue();
      // If longoption or shortoption can be passed as a one-char flag (e.g.
      // `-9`)
      if (val_int > 0 and val_int < CHAR_MAX) {
        char val = static_cast<char>(val_int);
        std::string s(1, val);
        this->currentCases.push_back(s);
      }
      // If the option can not be passed as a one-char flag (only longopts, e.g.
      // `--ignore`). Often passed as enum value
      else {
        E = E->IgnoreParenImpCasts();
        // If we can evaluate value as an enum value - proceed
        if (auto *declRef = llvm::dyn_cast<clang::DeclRefExpr>(E)) {
          std::string identifierName = declRef->getNameInfo().getAsString();
          this->currentCases.push_back(identifierName);
        }
        // Else - skip
      }
    }

    return true;
  }

  bool VisitBreakStmt(BreakStmt *S) {
    currentCases.clear();
    return true;
  }

  // /* functions visitor */
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
    for (int i = 0; i < call->getNumArgs(); i++) {

      Expr *arg = call->getArg(i)->IgnoreParenImpCasts();
      if (DeclRefExpr *dre = dyn_cast<DeclRefExpr>(arg)) {

        if (dre->getNameInfo().getAsString() == "optarg") {

          // If the case value is not a typeable char (for internal usage)
          // if (this->currentCases.empty()) {
          //   return true;
          // }

          // Gather all cases which converts optarg like that
          std::string cases{"- \'"};
          for (auto &sharedCase_ch : this->currentCases) {
            cases += sharedCase_ch;
            cases += ",";
          }
          cases.pop_back();
          cases += "':";

          // Gather types
          std::string types = inferTypeRecursive(name, {});

          llvm::outs() << "    " << cases << '\n';
          llvm::outs() << "        function: " << name << "\n";
          llvm::outs() << "        type: " << types << "\n";
          return true;
        }
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
          return *std::next(resultTypes.begin(), 1) + "\"";
        }

        // return the potential types (if there are branching instructions)
        std::string combined = "\n";
        for (const std::string &t : resultTypes) {
          combined += "        - " + t + "\n";
        }
        combined.pop_back();

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
