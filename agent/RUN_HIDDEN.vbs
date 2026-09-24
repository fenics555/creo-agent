' ЗАПУСК БЕЗ ОКНА (живая находка 24.09.2026: задачи дома мелькали консолью — «моргает синим»).
' Зов: wscript.exe RUN_HIDDEN.vbs "D:\путь\к\скрипту.bat"
Set sh = CreateObject("WScript.Shell")
If WScript.Arguments.Count > 0 Then
  sh.Run """" & WScript.Arguments(0) & """", 0, False
End If
Set sh = Nothing
