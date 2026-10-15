#ifndef __CONSOLECOMMANDS_H__
#define __CONSOLECOMMANDS_H__

#ifndef __CONCOMMAND_H__
#include "concommand.h"
#endif

// The main client console state, to be used with the concommand functions.
extern ConsoleState g_ClientConsoleState;


// Initializes all the base DirectEngine console variables.
void			c_InitConsoleCommands();
void			c_TermConsoleCommands();

// Call this to run a console command.
void			c_CommandHandler(const char *pCommand);

#ifdef NOLF2SRC_MODERN
// MODERN.md M-E5: a line typed into the console: run, then say what it did
// where the command handler is silent (a variable set, a name unknown).
void			c_ModernTypedCommand(const char *pCommand);

// MODERN.md M-E5: every command (the engine's and the game's) and every
// variable whose name starts with pPrefix, for Tab. A name can come twice
// (an engine variable that has been set is a console variable too).
typedef void	(*ModernNameFn)(const char *pName, void *pUser);
void			c_ModernEnumNames(const char *pPrefix, ModernNameFn fn, void *pUser);
#endif


#endif  // __CONSOLECOMMANDS_H__

