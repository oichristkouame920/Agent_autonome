Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
bat = root & "\AgentLocal.bat"
shell.Run Chr(34) & bat & Chr(34) & " start", 0, False
