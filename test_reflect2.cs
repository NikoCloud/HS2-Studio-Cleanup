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
            var types = asm.GetTypes().Where(t => t.Name.Contains("Chara") || t.Name.Contains("Card") || t.Name.Contains("Sex")).ToList();
            
            foreach (var t in types)
            {
                Console.WriteLine(t.FullName);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("Error: " + ex.Message);
        }
    }
}
