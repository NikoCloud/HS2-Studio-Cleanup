using System;
using System.Reflection;

class Program
{
    static void Main()
    {
        try
        {
            Assembly asm = Assembly.LoadFrom(@"C:\HS2\[UTILITY] KKManager\KKManager.Core.dll");
            Type loaderType = asm.GetType("KKManager.Data.Cards.CardLoader");
            MethodInfo loadMethod = loaderType.GetMethod("LoadCard", BindingFlags.Public | BindingFlags.Static, null, new Type[] { typeof(string) }, null);
            
            if (loadMethod != null)
            {
                Type cardType = asm.GetType("KKManager.Data.Cards.Card");
                PropertyInfo sexProp = cardType.GetProperty("Sex");
                
                string[] paths = new string[] {
                    @"C:\HS2\UserData\chara\female\BR-Chan HS2 Rev2.png",
                    @"C:\HS2\UserData\chara\female\Isabela.png",
                    @"C:\HS2\UserData\chara\male\HS2ChaM_20240408200000.png"
                };
                
                foreach (string path in paths)
                {
                    object card = loadMethod.Invoke(null, new object[] { path });
                    if (card != null && sexProp != null)
                    {
                        object sex = sexProp.GetValue(card, null);
                        Console.WriteLine(path + " => " + sex.ToString());
                    }
                    else
                    {
                        Console.WriteLine(path + " => Load failed or no Sex prop.");
                    }
                }
            }
            else
            {
                Console.WriteLine("Could not find LoadCard(string) on CardLoader.");
                foreach (var m in loaderType.GetMethods(BindingFlags.Public | BindingFlags.Static)) {
                    Console.WriteLine("Method: " + m.Name);
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("Error: " + ex.Message);
        }
    }
}
