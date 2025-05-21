using System;
using System.Diagnostics;
using System.Threading;

class Program
{
    static void Main()
    {
        
        string projectPath = @"C:\Users\egorc\OneDrive\Рабочий стол\Cursovaya\homework-tracker";  // ← замени на свой путь
        string pythonFile = "app.py";

        try
        {
            ProcessStartInfo start = new ProcessStartInfo
            {
                FileName = "cmd.exe",
                Arguments = $"/C python {pythonFile}",
                WorkingDirectory = projectPath,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            Process process = Process.Start(start);
            Console.WriteLine("Сайт запущен! Разработчики Макар и Мансур");

            
            Thread.Sleep(3000);

            
            Process.Start(new ProcessStartInfo("http://127.0.0.1:3000") { UseShellExecute = true });
        }
        catch (Exception ex)
        {
            Console.WriteLine("Ошибка: " + ex.Message);
        }
    }
}
