Option Explicit
' =============================================================================
' zotdocx · Word 侧配套宏：把 Zotero 正文引用号补回上标
'
' 什么时候要它：
'   `zotdocx patch` 让 Zotero 的正文引文改走纯文本写入（去掉 \super），
'   换来的是「无法删除范围」不再出现；代价是引用号变成平排。
'   本模块把每个 ZOTERO_ITEM 域的域结果设回上标。
'
' 作用范围：
'   只动域代码里含 ZOTERO_ITEM 的引注域。参考文献表（CSL_BIBLIOGRAPHY）
'   只统计、绝不改动，所以文献条目编号不会被误设成上标。
'
' 两种用法（装一次，选一种）：
'   手动：Alt+F8 → ZoteroFixCitationsSuper，定稿前跑一次。
'   自动：另装 WordEvents 类模块 + ThisDocument 里的 AutoExec，
'         每 TICK_SECONDS 秒巡检一次，缺上标就补，刷新完不用管。
'
' 安装步骤见 docs/word-superscript.zh-CN.md。
' =============================================================================

Private Const TICK_SECONDS As Long = 5
Private mBusy As Boolean
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

' 停止巡检（本模块的 Start/Stop 走标志位，比取消 OnTime 队列可靠）
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

' 立即补一次（供手动或外部调用）
Public Sub ZoteroFixNow()
    ZoteroFixCitationsSuper True
End Sub

' 主过程：把当前文档里所有 ZOTERO_ITEM 域的域结果设为上标
Public Sub ZoteroFixCitationsSuper(Optional ByVal Silent As Boolean = False)
    Dim doc As Document
    Dim f As Field
    Dim code As String
    Dim nCit As Long
    Dim nFixed As Long
    Dim nBib As Long

    If mBusy Then Exit Sub
    mBusy = True
    On Error GoTo finish

    If Documents.Count = 0 Then GoTo finish
    Set doc = ActiveDocument

    For Each f In doc.Fields
        On Error Resume Next
        code = f.Code.Text
        Err.Clear
        On Error GoTo finish
        If InStr(code, "ZOTERO_ITEM") > 0 Then
            nCit = nCit + 1
            If Not f.Result.Font.Superscript Then
                f.Result.Font.Superscript = True
                nFixed = nFixed + 1
            End If
        ElseIf InStr(code, "CSL_BIBLIOGRAPHY") > 0 Then
            nBib = nBib + 1
        End If
    Next f

finish:
    mBusy = False
    If Not Silent Then
        On Error Resume Next
        If nCit = 0 Then
            MsgBox "当前文档里没有找到 Zotero 引用域。" & vbCrLf & _
                   "（引用域代码里应含 ZOTERO_ITEM）", vbInformation, "zotdocx"
        Else
            MsgBox "Zotero 引用域：" & nCit & " 个" & vbCrLf & _
                   "本次补上标：" & nFixed & " 个" & vbCrLf & _
                   "参考文献表域（未改动）：" & nBib & " 个", vbInformation, "zotdocx"
        End If
        Err.Clear
    End If
End Sub

' 排查用：把每个引用域的文字与上标状态打到立即窗口（Alt+F11 → Ctrl+G）
Public Sub ZoteroCitationList()
    Dim doc As Document
    Dim f As Field
    Dim i As Long
    Dim n As Long

    If Documents.Count = 0 Then Exit Sub
    Set doc = ActiveDocument
    For Each f In doc.Fields
        If InStr(f.Code.Text, "ZOTERO_ITEM") > 0 Then
            i = i + 1
            Debug.Print i & vbTab & Replace(f.Result.Text, vbCr, "") & _
                        vbTab & "superscript=" & f.Result.Font.Superscript
            n = n + 1
        End If
    Next f
    MsgBox "已把 " & n & " 条引用写到立即窗口（Alt+F11 → Ctrl+G）", vbInformation, "zotdocx"
End Sub
