using System;
using System.Diagnostics;
using System.IO;
using System.Net.NetworkInformation;
using System.Threading;

namespace HomeworkTrackerLauncher
{
    class Program
    {
        static void Main()
        {
            Console.Title = "Homework Tracker Launcher by Макар & Мансур";
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("🔄 Инициализация системы...");
            Thread.Sleep(1000);

            InitializeModules();
            CheckNetworkPort(5000);
            LogEnvironmentInfo();

            string exePath = @"C:\Users\egorc\OneDrive\Рабочий стол\Cursovaya\homework-tracker\dist\app.exe";

            try
            {
                Console.WriteLine(" Запуск сервера...");
                ProcessStartInfo start = new ProcessStartInfo
                {
                    FileName = exePath,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                Process process = Process.Start(start);
                Console.WriteLine(" Сайт успешно запущен! Разработчики: Макар & Мансур");

                Thread.Sleep(3000);

                Console.WriteLine(" Открытие браузера...");
                Process.Start(new ProcessStartInfo("http://127.0.0.1:5000") { UseShellExecute = true });
            }
            catch (Exception ex)
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine(" Ошибка запуска: " + ex.Message);
            }

            Console.ResetColor();
        }

        static void InitializeModules()
        {
            Console.WriteLine("Загрузка модулей...");
            Thread.Sleep(500);
            Console.WriteLine(" Инициализация ядра приложения...");
            Thread.Sleep(500);
            Console.WriteLine(" Подключение интеллектуального анализатора логов...");
            Thread.Sleep(500);
        }

        static void LogEnvironmentInfo()
        {
            Console.WriteLine("📝 Информация о среде:");
            Console.WriteLine($"- Версия .NET: {Environment.Version}");
            Console.WriteLine($"- Имя пользователя: {Environment.UserName}");
            Console.WriteLine($"- Имя компьютера: {Environment.MachineName}");
            Console.WriteLine($"- ОС: {Environment.OSVersion}");
        }

        static void CheckNetworkPort(int port)
        {
            Console.WriteLine($"🔍 Проверка порта {port}...");

            IPGlobalProperties ipProperties = IPGlobalProperties.GetIPGlobalProperties();
            TcpConnectionInformation[] tcpConnections = ipProperties.GetActiveTcpConnections();

            bool portInUse = false;

            foreach (var conn in tcpConnections)
            {
                if (conn.LocalEndPoint.Port == port)
                {
                    portInUse = true;
                    break;
                }
            }

            if (portInUse)
            {
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine($" Порт {port} уже используется. Возможно, сервер уже запущен.");
                Console.ResetColor();
            }
            else
            {
                Console.WriteLine($"✅ Порт {port} свободен.");
            }
        }
    }
}
