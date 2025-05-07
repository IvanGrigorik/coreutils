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

#define return_visitor                                                         \
  { return true; }

using namespace clang;
using namespace clang::tooling;
using namespace llvm;
using namespace clang::ast_matchers;

static llvm::cl::OptionCategory ToolCategory("getopt-type-extractor");

class OptargVisitor : public RecursiveASTVisitor<OptargVisitor> {
public:
  explicit OptargVisitor(std::vector<std::unique_ptr<ASTUnit>> &ASTUnits)
      : ASTUnits(ASTUnits) {
    initTypeMap();
  }

  void analyzeAll() {
    for (const auto &AST : ASTUnits) {
      Context = &AST->getASTContext();
      TraverseDecl(Context->getTranslationUnitDecl());
    }
  }

  bool VisitCallExpr(CallExpr *call) {
    auto *callee = call->getDirectCallee();
    if (!callee) {
      return_visitor;
    }

    StringRef name = callee->getName();
    if (call->getNumArgs() < 0) {
      return_visitor;
    }

    Expr *arg = call->getArg(0)->IgnoreParenImpCasts();
    if (DeclRefExpr *dre = dyn_cast<DeclRefExpr>(arg)) {

      if (dre->getNameInfo().getAsString() == "optarg") {
        llvm::outs() << "optarg used in function: " << name << "\n";
        llvm::outs() << "Resolved from file: ";
        if (callee->getLocation().isValid()) {
          llvm::outs() << Context->getSourceManager().getFilename(
                              callee->getLocation())
                       << "\n";
        } else {
          llvm::outs() << "<unknown>\n";
        }
        llvm::outs() << "Inferred type: " << inferTypeRecursive(name, {})
                     << "\n";
      }
    }
    return true;
  }

private:
  std::vector<std::unique_ptr<ASTUnit>> &ASTUnits;
  ASTContext *Context;
  std::map<std::string, std::string> FuncTypeMap;

  void initTypeMap() {
    FuncTypeMap = {{"atoi", "int"},
                   {"atol", "long"},
                   {"atoll", "long long"},
                   {"strdup", "char *"},
                   {"strndup", "char *"},
                   {"strcpy", "char *"},
                   {"strncpy", "char *"},
                   {"strcat", "char *"},
                   {"strncat", "char *"},
                   {"strtol", "long"},
                   {"strtoul", "unsigned long"},
                   {"strtoll", "long long"},
                   {"strtoull", "unsigned long long"},
                   {"sscanf", "mixed"},
                   {"memcpy", "raw"},
                   {"sprintf", "formatted string"},
                   {"snprintf", "formatted string"}};
  }

  std::string inferTypeRecursive(StringRef funcName,
                                 std::set<std::string> visited) {
    std::string fname = funcName.str();
    if (FuncTypeMap.count(fname)) {
      return FuncTypeMap[fname];
    }
    if (visited.count(fname))
      return "unknown";
    visited.insert(fname);

    for (const auto &AST : ASTUnits) {
      TranslationUnitDecl *tu = AST->getASTContext().getTranslationUnitDecl();
      for (auto *decl : tu->decls()) {
        if (auto *fd = dyn_cast<FunctionDecl>(decl)) {
          if (fd->getNameAsString() == fname && fd->hasBody()) {
            std::set<std::string> resultTypes =
                gatherTypesFromStmt(fd->getBody(), visited);
            if (!resultTypes.empty()) {
              std::string combined = "potential: ";
              for (const std::string &t : resultTypes) {
                combined += t + ", ";
              }
              combined.pop_back();
              combined.pop_back();
              return combined;
            }
          }
        }
      }
    }
    return "unknown";
  }

  std::set<std::string> gatherTypesFromStmt(Stmt *stmt,
                                            std::set<std::string> &visited) {
    std::set<std::string> types;
    if (!stmt)
      return types;

    for (Stmt *child : stmt->children()) {
      if (!child)
        continue;

      if (CallExpr *call = dyn_cast<CallExpr>(child)) {
        if (FunctionDecl *fd = call->getDirectCallee()) {
          std::string name = fd->getNameAsString();
          std::string inferred = inferTypeRecursive(name, visited);
          if (inferred != "unknown")
            types.insert(inferred);
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

  ClangTool Tool(OptionsParser.getCompilations(),
                 OptionsParser.getSourcePathList());

  // Trying to builds ASTs
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
