using System;
using System.Reflection;
using System.Linq;

class Program
{
    static void Main()
    {
        try
        {
            Assembly asm = Assembly.LoadFrom(@"C:\HS2\[UTILITY] KKManager\KKManager.Core.dll");
            Console.WriteLine("Loaded Assembly: " + asm.FullName);
            
            var types = asm.GetTypes().Where(t => t.Name.Contains("Chara") || t.Name.Contains("Card")).ToList();
            Console.WriteLine("Found Types: " + types.Count);
            
            foreach (var t in types)
            {
                if (t.Name == "CharaCard" || t.Name == "CharaCardData" || t.Name.Contains("CardParser"))
                {
                    Console.WriteLine("\n--- " + t.FullName + " ---");
                    foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static))
                    {
                        Console.WriteLine("Method: " + m.Name);
                    }
                    foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static))
                    {
                        Console.WriteLine("Property: " + p.Name + " (" + p.PropertyType.Name + ")");
                    }
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("Error: " + ex);
        }
    }
}
