Option Explicit
' =============================================================================
' zotdocx · Word 侧配套宏（自动巡检版）
'
' 依赖（必须先装好，否则本模块编译不过）：
'   * ZoteroFixManual.bas  —— 提供 ZoteroFixCitationsSuper
'   * WordEvents.cls       —— 类模块，名字必须是 WordEvents
'   * ThisDocument 里的 AutoExec（见 ThisDocument.txt）
'
' 作用：每 TICK_SECONDS 秒看一次当前文档，发现任何一个引注域缺上标，
'       就把全部引注域扫一遍补上。所以打完补丁之后刷新引用不用管。
'
' 停掉：立即窗口（Ctrl+G）执行 ZoteroFixStop；重启 Word 恢复。
' =============================================================================

Private Const TICK_SECONDS As Long = 5
Private mStopped As Boolean

' 挂 WithEvents 的实例必须声明在标准模块里并保持存活
Public WordEventsApp As WordEvents

' 由 ThisDocument 的 AutoExec 调用：挂事件钩子 + 启动巡检
Public Sub WordEventsInit()
    On Error Resume Next
    If WordEventsApp Is Nothing Then
        Set WordEventsApp = New WordEvents
        Set WordEventsApp.App = Application
    End If
    WordEventsKick
    Err.Clear
End Sub

' 打开 / 新建 / 切换文档时踢一次，保证新文档也纳入巡检
Public Sub WordEventsKick()
    On Error Resume Next
    mStopped = False
    Application.OnTime When:=Now + TimeSerial(0, 0, 1), Name:="ZoteroFixTick"
    Err.Clear
End Sub

' 停止巡检
Public Sub ZoteroFixStop()
    mStopped = True
End Sub

' 巡检：只要发现有一个引注域缺上标，就把全部引注域扫一遍补上
Public Sub ZoteroFixTick()
    Dim doc As Document
    Dim f As Field
    Dim code As String
    Dim needFix As Boolean

    On Error Resume Next
    If mStopped Then Exit Sub
    If Documents.Count > 0 Then
        Set doc = ActiveDocument
        For Each f In doc.Fields
            code = f.Code.Text
            If InStr(code, "ZOTERO_ITEM") > 0 Then
                If Not f.Result.Font.Superscript Then
                    needFix = True
                    Exit For
                End If
            End If
        Next f
        If needFix Then ZoteroFixCitationsSuper True
    End If
    If Err.Number <> 0 Then Err.Clear
    Application.OnTime When:=Now + TimeSerial(0, 0, TICK_SECONDS), Name:="ZoteroFixTick"
End Sub
