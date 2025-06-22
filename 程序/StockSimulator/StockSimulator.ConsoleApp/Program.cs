namespace StockSimulator.ConsoleApp
{
    internal class Program
    {
        static void Main(string[] args)
        {
            //价格随机生成器
            decimal initPrice = 10m;
            int rndFactor = Random.Shared.Next(-10, 10); 
            decimal price = initPrice + (rndFactor / 100m) * initPrice;

            Console.WriteLine("Hello, World!");
        }
    }
}
