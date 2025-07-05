namespace StockStudy
{
    using Microsoft.Extensions.DependencyInjection;
    using StockStudy.Configuration; 
    using System;
    using System.Threading;

    internal static class Program
    {
        /// <summary>
        ///  The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main()
        {
            // To customize application configuration such as set high DPI settings or default font,
            // see https://aka.ms/applicationconfiguration.
            ApplicationConfiguration.Initialize();
            var provider = AddServices(new ServiceCollection()).BuildServiceProvider();
            provider.InitService();
            provider.RunApp();
        }


        static void RunApp(this IServiceProvider provider)
        {
            Application.Run(provider.GetRequiredService<MainForm>());
            Application.ThreadException += Application_ThreadException;
        }


        static IServiceCollection AddServices(IServiceCollection services)
        {
            //register configuration 
            var configuration = ConfigurationHelper.BuildConfiguration();
            services.AddSingleton(configuration);

            services.AddAllServices(configuration);

            // register form
            services.AddScoped<MainForm>();

            return services;
        }

        static void Application_ThreadException(object sender, ThreadExceptionEventArgs e)
        {
            // TODO: log
        }
    }
}