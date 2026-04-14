using System;
using System.Reflection;
using System.Linq;

class Program
{
    static void Main()
    {
        Assembly asm = Assembly.LoadFrom(@"C:\HS2\[UTILITY] KKManager\KKManager.Core.dll");
        var types = new string[] { "KKManager.Data.Cards.CardLoader", "KKManager.Data.Cards.Card", "KKManager.Data.Cards.AI.AiCard" };
        
        foreach (var tName in types)
        {
            var t = asm.GetType(tName);
            if (t == null) continue;
            Console.WriteLine("\n=== " + tName + " ===");
            foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Static).OrderBy(m => m.Name))
            {
                var pParams = string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name));
                Console.WriteLine($"Static {m.ReturnType.Name} {m.Name}({pParams})");
            }
            foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Instance).OrderBy(m => m.Name).Take(5))
            {
                var pParams = string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name));
                Console.WriteLine($"Instance {m.ReturnType.Name} {m.Name}({pParams})");
            }
        }
    }
}
