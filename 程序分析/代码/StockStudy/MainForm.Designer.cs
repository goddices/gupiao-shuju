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
            buttonApi = new Button();
            buttonFile = new Button();
            openFileDialog1 = new OpenFileDialog();
            markketSH = new RadioButton();
            marketSZ = new RadioButton();
            stockCodeInput = new TextBox();
            labelCode = new Label();
            logArea = new TextBox();
            adjustSelect = new ComboBox();
            periodSelect = new ComboBox();
            groupBox1 = new GroupBox();
            myAnyTestStrategy = new RadioButton();
            dollerCostAveragingStrategy = new RadioButton();
            groupBox1.SuspendLayout();
            SuspendLayout();
            // 
            // buttonApi
            // 
            buttonApi.Location = new Point(807, 20);
            buttonApi.Name = "buttonApi";
            buttonApi.Size = new Size(94, 29);
            buttonApi.TabIndex = 0;
            buttonApi.Text = "接口方式";
            buttonApi.UseVisualStyleBackColor = true;
            buttonApi.Click += ButtonApi_Click;
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
            // logArea
            // 
            logArea.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            logArea.Location = new Point(25, 146);
            logArea.Multiline = true;
            logArea.Name = "logArea";
            logArea.ScrollBars = ScrollBars.Vertical;
            logArea.Size = new Size(992, 385);
            logArea.TabIndex = 6;
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
            // groupBox1
            // 
            groupBox1.Controls.Add(myAnyTestStrategy);
            groupBox1.Controls.Add(dollerCostAveragingStrategy);
            groupBox1.Location = new Point(21, 55);
            groupBox1.Name = "groupBox1";
            groupBox1.Size = new Size(478, 85);
            groupBox1.TabIndex = 9;
            groupBox1.TabStop = false;
            // 
            // myAnyTestStrategy
            // 
            myAnyTestStrategy.AutoSize = true;
            myAnyTestStrategy.Location = new Point(195, 37);
            myAnyTestStrategy.Name = "myAnyTestStrategy";
            myAnyTestStrategy.Size = new Size(150, 24);
            myAnyTestStrategy.TabIndex = 1;
            myAnyTestStrategy.Text = "我随便测测的策略";
            myAnyTestStrategy.UseVisualStyleBackColor = true;
            // 
            // dollerCostAveragingStrategy
            // 
            dollerCostAveragingStrategy.AutoSize = true;
            dollerCostAveragingStrategy.Checked = true;
            dollerCostAveragingStrategy.Location = new Point(25, 37);
            dollerCostAveragingStrategy.Name = "dollerCostAveragingStrategy";
            dollerCostAveragingStrategy.Size = new Size(90, 24);
            dollerCostAveragingStrategy.TabIndex = 0;
            dollerCostAveragingStrategy.TabStop = true;
            dollerCostAveragingStrategy.Text = "定投策略";
            dollerCostAveragingStrategy.UseVisualStyleBackColor = true;
            // 
            // MainForm
            // 
            AutoScaleDimensions = new SizeF(9F, 20F);
            AutoScaleMode = AutoScaleMode.Font;
            ClientSize = new Size(1044, 560);
            Controls.Add(groupBox1);
            Controls.Add(periodSelect);
            Controls.Add(adjustSelect);
            Controls.Add(logArea);
            Controls.Add(labelCode);
            Controls.Add(stockCodeInput);
            Controls.Add(marketSZ);
            Controls.Add(markketSH);
            Controls.Add(buttonFile);
            Controls.Add(buttonApi);
            Name = "MainForm";
            StartPosition = FormStartPosition.CenterScreen;
            Text = "我的量化策略分析工具";
            Load += Form1_Load;
            groupBox1.ResumeLayout(false);
            groupBox1.PerformLayout();
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
        private TextBox logArea;
        private ComboBox adjustSelect;
        private ComboBox periodSelect;
        private GroupBox groupBox1;
        private RadioButton myAnyTestStrategy;
        private RadioButton dollerCostAveragingStrategy;
    }
}
