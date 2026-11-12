Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
launcher = root & "\runtime\start_agentlocal_gui.vbs"
icon = root & "\assets\agentlocal.ico"

desktop = shell.SpecialFolders("Desktop")
programs = shell.SpecialFolders("Programs")

Call CreateShortcut(desktop & "\AgentLocal.lnk")
Call CreateShortcut(programs & "\AgentLocal.lnk")

Sub CreateShortcut(path)
    Set link = shell.CreateShortcut(path)
    link.TargetPath = "wscript.exe"
    link.Arguments = Chr(34) & launcher & Chr(34)
    link.WorkingDirectory = root
    link.Description = "Lancer AgentLocal"
    If fso.FileExists(icon) Then
        link.IconLocation = icon & ",0"
    End If
    link.Save
End Sub
