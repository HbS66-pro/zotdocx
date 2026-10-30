Option Explicit
' =============================================================================
' zotdocx · Word 应用事件类模块
'
' 装法：Normal.dotm 里插入一个【类模块】，把本文件内容粘进去，
'       在属性窗口把类模块名字改成 WordEvents（代码里 New WordEvents 认这个名字）。
' =============================================================================

Public WithEvents App As Word.Application

Private Sub App_DocumentOpen(ByVal Doc As Document)
    On Error Resume Next
    WordEventsKick
    Err.Clear
End Sub

Private Sub App_NewDocument(ByVal Doc As Document)
    On Error Resume Next
    WordEventsKick
    Err.Clear
End Sub

Private Sub App_WindowActivate(ByVal Doc As Document, ByVal Wn As Window)
    On Error Resume Next
    WordEventsKick
    Err.Clear
End Sub
