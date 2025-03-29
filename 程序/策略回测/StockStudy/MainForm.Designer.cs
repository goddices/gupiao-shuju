namespace StockStudy
{
    partial class MainForm
    {
        /// <summary>
        ///  Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        ///  Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        ///  Required method for Designer support - do not modify
        ///  the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            buttonFile = new Button();
            openFileDialog1 = new OpenFileDialog();
            markketSH = new RadioButton();
            marketSZ = new RadioButton();
            stockCodeInput = new TextBox();
            labelCode = new Label();
            textboxLogger = new TextBox();
            adjustSelect = new ComboBox();
            periodSelect = new ComboBox();
            stragtegyBox = new GroupBox();
            buttonTestPy = new Button();
            button1 = new Button();
            chartBox = new PictureBox();
            ButtonZoomOut = new Button();
            ButtonZoomIn = new Button();
            labelFocusQuote = new Label();
            ((System.ComponentModel.ISupportInitialize)chartBox).BeginInit();
            SuspendLayout();
            // 
            // buttonFile
            // 
            buttonFile.Location = new Point(926, 20);
            buttonFile.Name = "buttonFile";
            buttonFile.Size = new Size(94, 29);
            buttonFile.TabIndex = 1;
            buttonFile.Text = "文件方式";
            buttonFile.UseVisualStyleBackColor = true;
            buttonFile.Click += ButtonFile_Click;
            // 
            // openFileDialog1
            // 
            openFileDialog1.FileName = "openFileDialog1";
            // 
            // markketSH
            // 
            markketSH.AutoSize = true;
            markketSH.Checked = true;
            markketSH.Location = new Point(25, 22);
            markketSH.Name = "markketSH";
            markketSH.Size = new Size(60, 24);
            markketSH.TabIndex = 2;
            markketSH.TabStop = true;
            markketSH.Text = "沪市";
            markketSH.UseVisualStyleBackColor = true;
            // 
            // marketSZ
            // 
            marketSZ.AutoSize = true;
            marketSZ.Location = new Point(103, 22);
            marketSZ.Name = "marketSZ";
            marketSZ.Size = new Size(60, 24);
            marketSZ.TabIndex = 3;
            marketSZ.TabStop = true;
            marketSZ.Text = "深市";
            marketSZ.UseVisualStyleBackColor = true;
            // 
            // stockCodeInput
            // 
            stockCodeInput.Location = new Point(240, 22);
            stockCodeInput.Name = "stockCodeInput";
            stockCodeInput.Size = new Size(178, 27);
            stockCodeInput.TabIndex = 4;
            // 
            // labelCode
            // 
            labelCode.AutoSize = true;
            labelCode.Location = new Point(181, 25);
            labelCode.Name = "labelCode";
            labelCode.Size = new Size(39, 20);
            labelCode.TabIndex = 5;
            labelCode.Text = "代码";
            // 
            // textboxLogger
            // 
            textboxLogger.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            textboxLogger.Location = new Point(25, 495);
            textboxLogger.Multiline = true;
            textboxLogger.Name = "textboxLogger";
            textboxLogger.ScrollBars = ScrollBars.Vertical;
            textboxLogger.Size = new Size(992, 126);
            textboxLogger.TabIndex = 6;
            // 
            // adjustSelect
            // 
            adjustSelect.DropDownStyle = ComboBoxStyle.DropDownList;
            adjustSelect.FormattingEnabled = true;
            adjustSelect.Location = new Point(441, 21);
            adjustSelect.Name = "adjustSelect";
            adjustSelect.Size = new Size(151, 28);
            adjustSelect.TabIndex = 7;
            // 
            // periodSelect
            // 
            periodSelect.DropDownStyle = ComboBoxStyle.DropDownList;
            periodSelect.FormattingEnabled = true;
            periodSelect.Location = new Point(626, 21);
            periodSelect.Name = "periodSelect";
            periodSelect.Size = new Size(151, 28);
            periodSelect.TabIndex = 8;
            // 
            // stragtegyBox
            // 
            stragtegyBox.Location = new Point(103, 55);
            stragtegyBox.Name = "stragtegyBox";
            stragtegyBox.Size = new Size(584, 68);
            stragtegyBox.TabIndex = 9;
            stragtegyBox.TabStop = false;
            // 
            // buttonTestPy
            // 
            buttonTestPy.Location = new Point(923, 77);
            buttonTestPy.Name = "buttonTestPy";
            buttonTestPy.Size = new Size(94, 29);
            buttonTestPy.TabIndex = 10;
            buttonTestPy.Text = "PyTest";
            buttonTestPy.UseVisualStyleBackColor = true;
            buttonTestPy.Click += ButtonTestPy_Click;
            // 
            // button1
            // 
            button1.Location = new Point(815, 20);
            button1.Name = "button1";
            button1.Size = new Size(94, 29);
            button1.TabIndex = 11;
            button1.Text = "接口方式";
            button1.UseVisualStyleBackColor = true;
            button1.Click += ButtonApi_Click;
            // 
            // chartBox
            // 
            chartBox.Location = new Point(25, 177);
            chartBox.Name = "chartBox";
            chartBox.Size = new Size(992, 299);
            chartBox.TabIndex = 12;
            chartBox.TabStop = false;
            chartBox.Paint += ChartBox_Paint;
            chartBox.MouseLeave += ChartBox_MouseLeave;
            chartBox.MouseMove += ChartBox_MouseMove;
            // 
            // ButtonZoomOut
            // 
            ButtonZoomOut.Location = new Point(25, 142);
            ButtonZoomOut.Name = "ButtonZoomOut";
            ButtonZoomOut.Size = new Size(28, 29);
            ButtonZoomOut.TabIndex = 13;
            ButtonZoomOut.Text = "-";
            ButtonZoomOut.UseVisualStyleBackColor = true;
            ButtonZoomOut.Click += ButtonZoomOut_Click;
            // 
            // ButtonZoomIn
            // 
            ButtonZoomIn.Location = new Point(59, 142);
            ButtonZoomIn.Name = "ButtonZoomIn";
            ButtonZoomIn.Size = new Size(28, 29);
            ButtonZoomIn.TabIndex = 14;
            ButtonZoomIn.Text = "+";
            ButtonZoomIn.UseVisualStyleBackColor = true;
            ButtonZoomIn.Click += ButtonZoomIn_Click;
            // 
            // labelFocusQuote
            // 
            labelFocusQuote.AutoSize = true;
            labelFocusQuote.Location = new Point(218, 148);
            labelFocusQuote.Name = "labelFocusQuote";
            labelFocusQuote.Size = new Size(0, 20);
            labelFocusQuote.TabIndex = 15;
            // 
            // MainForm
            // 
            AutoScaleDimensions = new SizeF(9F, 20F);
            AutoScaleMode = AutoScaleMode.Font;
            ClientSize = new Size(1044, 633);
            Controls.Add(labelFocusQuote);
            Controls.Add(ButtonZoomIn);
            Controls.Add(ButtonZoomOut);
            Controls.Add(chartBox);
            Controls.Add(button1);
            Controls.Add(buttonTestPy);
            Controls.Add(stragtegyBox);
            Controls.Add(periodSelect);
            Controls.Add(adjustSelect);
            Controls.Add(textboxLogger);
            Controls.Add(labelCode);
            Controls.Add(stockCodeInput);
            Controls.Add(marketSZ);
            Controls.Add(markketSH);
            Controls.Add(buttonFile);
            Name = "MainForm";
            StartPosition = FormStartPosition.CenterScreen;
            Text = "我的量化策略分析工具";
            Load += MainForm_Load;
            ((System.ComponentModel.ISupportInitialize)chartBox).EndInit();
            ResumeLayout(false);
            PerformLayout();
        }

        #endregion

        private Button buttonApi;
        private Button buttonFile;
        private OpenFileDialog openFileDialog1;
        private RadioButton markketSH;
        private RadioButton marketSZ;
        private TextBox stockCodeInput;
        private Label labelCode;
        private TextBox textboxLogger;
        private ComboBox adjustSelect;
        private ComboBox periodSelect;
        private GroupBox stragtegyBox;
        private RadioButton myAnyTestStrategy;
        private RadioButton dollerCostAveragingStrategy;
        private Button buttonTestPy;
        private Button button1;
        private PictureBox chartBox;
        private Button ButtonZoomOut;
        private Button ButtonZoomIn;
        private Label labelFocusQuote;
    }
}
