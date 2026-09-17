# -*- coding: utf-8 -*-
# ============================================================
#  Visual Dashboard System — 图形化运行控制台 (v5 · WPF)
#  采用 WPF(XAML) + PowerShell 加载,完全免安装免编译。
#  视觉风格:macOS / iOS 简洁风(主色 AppleBlue #007AFF)
#  功能区:标题栏 / 左侧导航 / 顶部状态卡 / 步骤进度 / Tab 多页签
# ============================================================

# ---------- 加载 WPF 程序集 ----------
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Xaml
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$script:BaseDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

# ---------- Boot 标记日志(诊断:若启动失败可看停在哪一步) ----------
function Write-BootLog([string]$msg) {
    try {
        $f = Join-Path $script:BaseDir 'logs\launcher_boot.log'
        Add-Content -Path $f -Value "[$(Get-Date -Format 'HH:mm:ss.fff')] $msg" -Encoding UTF8
    } catch { }
}
Write-BootLog '===== 启动器开始 ====='

# ---------- 全局 Dispatcher 异常兜底(避免无声崩溃/闪退) ----------
# WPF 事件处理器(如按钮 Click)内抛异常会走 Dispatcher,若不处理则进程直接终止
$app = [System.Windows.Application]::Current
if (-not $app) { $app = New-Object System.Windows.Application }
$script:appError = $null
$app.add_DispatcherUnhandledException({
    param($sender, $e)
    try {
        $script:appError = $e.Exception
        $errFile = Join-Path $script:BaseDir 'logs\launcher_error.log'
        Add-Content -Path $errFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Dispatcher异常: $($e.Exception.ToString())" -Encoding UTF8
        # 尝试在日志框里提示(若 UI 已就绪)
        if ($controls -and $controls.LogBox) {
            $controls.LogBox.AppendText("`r`n[!!] 发生内部错误,详情见 logs\launcher_error.log`r`n$($e.Exception.Message)`r`n")
        }
    } catch { }
    $e.Handled = $true  # 吞掉,不让进程崩溃
})
Write-BootLog 'dispatcher handler ready'

# ---------- XAML (macOS / iOS 简洁风) ----------
[xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="销售运营可视化看板系统"
        Width="1180" Height="740" MinWidth="980" MinHeight="600"
        WindowStartupLocation="CenterScreen"
        Background="#F5F5F7" FontFamily="Segoe UI, Microsoft YaHei UI" FontSize="13"
        Foreground="#1D1D1F" TextOptions.TextFormattingMode="Display">
  <Window.Resources>
    <!-- 苹果系调色板 -->
    <SolidColorBrush x:Key="AppleBlue"      Color="#007AFF"/>
    <SolidColorBrush x:Key="AppleBlueHover" Color="#0A84FF"/>
    <SolidColorBrush x:Key="AppleGreen"     Color="#34C759"/>
    <SolidColorBrush x:Key="AppleRed"       Color="#FF3B30"/>
    <SolidColorBrush x:Key="AppleOrange"    Color="#FF9500"/>
    <SolidColorBrush x:Key="BgPage"         Color="#F5F5F7"/>
    <SolidColorBrush x:Key="BgCard"         Color="#FFFFFF"/>
    <SolidColorBrush x:Key="BgSidebar"      Color="#F9F9FB"/>
    <SolidColorBrush x:Key="BgHover"        Color="#EFEFF1"/>
    <SolidColorBrush x:Key="BdLine"         Color="#E5E5EA"/>
    <SolidColorBrush x:Key="TxtBlack"       Color="#1D1D1F"/>
    <SolidColorBrush x:Key="TxtMuted"       Color="#6E6E73"/>
    <SolidColorBrush x:Key="TxtLabel"       Color="#86868B"/>
    <SolidColorBrush x:Key="SegBg"          Color="#EFEFF4"/>
    <SolidColorBrush x:Key="SegFg"          Color="#FFFFFF"/>

    <!-- 主按钮(苹果蓝胶囊) -->
    <Style x:Key="PrimaryBtn" TargetType="Button">
      <Setter Property="Background" Value="{StaticResource AppleBlue}"/>
      <Setter Property="Foreground" Value="White"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Padding" Value="0"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="Bd" CornerRadius="10" Background="{TemplateBinding Background}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" Margin="20,9"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="{StaticResource AppleBlueHover}"/>
              </Trigger>
              <Trigger Property="IsEnabled" Value="False">
                <Setter TargetName="Bd" Property="Background" Value="#C7C7CC"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- 次按钮(白底+细灰边) -->
    <Style x:Key="AuxBtn" TargetType="Button" BasedOn="{StaticResource PrimaryBtn}">
      <Setter Property="Background" Value="White"/>
      <Setter Property="Foreground" Value="{StaticResource TxtBlack}"/>
      <Setter Property="FontWeight" Value="Normal"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="Bd" CornerRadius="10" Background="{TemplateBinding Background}"
                    BorderBrush="{StaticResource BdLine}" BorderThickness="1">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" Margin="16,7"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="{StaticResource BgHover}"/>
              </Trigger>
              <Trigger Property="IsEnabled" Value="False">
                <Setter TargetName="Bd" Property="Background" Value="#F2F2F7"/>
                <Setter Property="Foreground" Value="#C7C7CC"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- 危险按钮 -->
    <Style x:Key="DangerBtn" TargetType="Button" BasedOn="{StaticResource PrimaryBtn}">
      <Setter Property="Background" Value="{StaticResource AppleRed}"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="Bd" CornerRadius="10" Background="{TemplateBinding Background}">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center" Margin="20,9"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="#FF453A"/>
              </Trigger>
              <Trigger Property="IsEnabled" Value="False">
                <Setter TargetName="Bd" Property="Background" Value="#C7C7CC"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- 列表式侧栏按钮(iOS 风格:无边框,hover 浅灰) -->
    <Style x:Key="NavItem" TargetType="Button">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Foreground" Value="{StaticResource TxtBlack}"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Padding" Value="0"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="HorizontalContentAlignment" Value="Left"/>
      <Setter Property="FontSize" Value="13.5"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="Bd" CornerRadius="8" Background="{TemplateBinding Background}" Padding="14,10">
              <ContentPresenter HorizontalAlignment="Left" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="{StaticResource BgHover}"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- 状态卡(白底细边圆角) -->
    <Style x:Key="StatCard" TargetType="Border">
      <Setter Property="Background" Value="{StaticResource BgCard}"/>
      <Setter Property="CornerRadius" Value="12"/>
      <Setter Property="Padding" Value="18,16"/>
      <Setter Property="Margin" Value="0,0,12,0"/>
      <Setter Property="BorderBrush" Value="{StaticResource BdLine}"/>
      <Setter Property="BorderThickness" Value="1"/>
    </Style>

    <!-- iOS 分段控件专用样式(不重写 ControlTemplate,保留 Button 默认外观,避免 UIA Automation 异常) -->
    <Style x:Key="SegBtn" TargetType="Button">
      <Setter Property="Background" Value="Transparent"/>
      <Setter Property="Foreground" Value="{StaticResource TxtBlack}"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="FontSize" Value="13"/>
      <Setter Property="FontWeight" Value="Normal"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="Button">
            <Border x:Name="Bd" CornerRadius="7" Background="{TemplateBinding Background}" Padding="20,6">
              <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsMouseOver" Value="True">
                <Setter TargetName="Bd" Property="Background" Value="#F2F2F7"/>
              </Trigger>
              <Trigger Property="IsEnabled" Value="False">
                <Setter Property="Foreground" Value="#C7C7CC"/>
              </Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>

    <!-- 分组小标题 -->
    <Style x:Key="SectionTitle" TargetType="TextBlock">
      <Setter Property="FontSize" Value="11"/>
      <Setter Property="FontWeight" Value="SemiBold"/>
      <Setter Property="Foreground" Value="{StaticResource TxtLabel}"/>
      <Setter Property="Margin" Value="0,0,0,8"/>
    </Style>
  </Window.Resources>

  <Grid>
    <Grid.RowDefinitions>
      <RowDefinition Height="56"/>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
      <RowDefinition Height="32"/>
    </Grid.RowDefinitions>

    <!-- 顶栏(细工具条,无绿底) -->
    <Border Grid.Row="0" Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="0,0,0,1">
      <Grid Margin="20,0">
        <Grid.ColumnDefinitions>
          <ColumnDefinition Width="*"/>
          <ColumnDefinition Width="Auto"/>
        </Grid.ColumnDefinitions>
        <StackPanel Grid.Column="0" Orientation="Horizontal" VerticalAlignment="Center">
          <TextBlock Text="销售运营可视化看板系统" Foreground="{StaticResource TxtBlack}" FontSize="15" FontWeight="SemiBold" VerticalAlignment="Center"/>
          <Border Background="{StaticResource SegBg}" CornerRadius="4" Padding="8,3" Margin="14,0,0,0" VerticalAlignment="Center">
            <TextBlock Text="控制台" Foreground="{StaticResource TxtMuted}" FontSize="11"/>
          </Border>
        </StackPanel>
        <StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Center">
          <Ellipse x:Name="DotHeader" Width="8" Height="8" Fill="{StaticResource AppleGreen}" VerticalAlignment="Center"/>
          <TextBlock x:Name="LblHeaderStatus" Text="就绪" Foreground="{StaticResource TxtMuted}" FontSize="12.5" VerticalAlignment="Center" Margin="8,0,0,0"/>
        </StackPanel>
      </Grid>
    </Border>

    <!-- 状态卡 + 进度 -->
    <Border Grid.Row="1" Padding="20,16">
      <Grid>
        <Grid.RowDefinitions>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>

        <!-- 状态卡 -->
        <Grid Grid.Row="0" Margin="0,0,0,16">
          <Grid.ColumnDefinitions>
            <ColumnDefinition Width="*"/>
            <ColumnDefinition Width="*"/>
            <ColumnDefinition Width="*"/>
            <ColumnDefinition Width="*"/>
          </Grid.ColumnDefinitions>
          <Border Grid.Column="0" Style="{StaticResource StatCard}">
            <StackPanel>
              <TextBlock Text="年度累计区间" Style="{StaticResource SectionTitle}"/>
              <TextBlock x:Name="LblStatYear" Text="—" FontSize="16" FontWeight="SemiBold" Foreground="{StaticResource TxtBlack}" Margin="0,2,0,0"/>
              <TextBlock x:Name="LblStatYearHint" Text="—" FontSize="11.5" Foreground="{StaticResource TxtMuted}" Margin="0,6,0,0"/>
            </StackPanel>
          </Border>
          <Border Grid.Column="1" Style="{StaticResource StatCard}">
            <StackPanel>
              <TextBlock Text="月度数据" Style="{StaticResource SectionTitle}"/>
              <TextBlock x:Name="LblStatMonth" Text="—" FontSize="16" FontWeight="SemiBold" Foreground="{StaticResource TxtBlack}" Margin="0,2,0,0"/>
              <TextBlock x:Name="LblStatMonthHint" Text="—" FontSize="11.5" Foreground="{StaticResource TxtMuted}" Margin="0,6,0,0"/>
            </StackPanel>
          </Border>
          <Border Grid.Column="2" Style="{StaticResource StatCard}">
            <StackPanel>
              <TextBlock Text="结算模式" Style="{StaticResource SectionTitle}"/>
              <TextBlock x:Name="LblStatMode" Text="—" FontSize="16" FontWeight="SemiBold" Foreground="{StaticResource AppleBlue}" Margin="0,2,0,0"/>
              <TextBlock x:Name="LblStatModeHint" Text="—" FontSize="11.5" Foreground="{StaticResource TxtMuted}" Margin="0,6,0,0" TextWrapping="Wrap"/>
            </StackPanel>
          </Border>
          <Border Grid.Column="3" Style="{StaticResource StatCard}" Margin="0">
            <StackPanel>
              <TextBlock Text="最近产物" Style="{StaticResource SectionTitle}"/>
              <TextBlock x:Name="LblStatLatest" Text="—" FontSize="14" FontWeight="SemiBold" Foreground="{StaticResource TxtBlack}" Margin="0,2,0,0" TextTrimming="CharacterEllipsis"/>
              <TextBlock x:Name="LblStatLatestHint" Text="—" FontSize="11.5" Foreground="{StaticResource TxtMuted}" Margin="0,6,0,0"/>
            </StackPanel>
          </Border>
        </Grid>

        <!-- 阶段进度(iOS 风:细条 + 第 x/7 文字) -->
        <Grid Grid.Row="1">
          <Grid.ColumnDefinitions>
            <ColumnDefinition Width="*"/>
            <ColumnDefinition Width="Auto"/>
          </Grid.ColumnDefinitions>
          <StackPanel Grid.Column="0">
            <Grid Margin="0,0,0,8">
              <Grid.ColumnDefinitions>
                <ColumnDefinition Width="*"/>
                <ColumnDefinition Width="Auto"/>
              </Grid.ColumnDefinitions>
              <TextBlock Grid.Column="0" Text="运行进度" Style="{StaticResource SectionTitle}"/>
              <TextBlock Grid.Column="1" x:Name="LblPhaseText" Text="第 0 / 7 阶段" FontSize="11" Foreground="{StaticResource TxtMuted}"/>
            </Grid>
            <Grid x:Name="PhasePanel">
              <!-- 阶段 chip 由代码动态生成 -->
            </Grid>
            <ProgressBar x:Name="PhaseProgress" Height="4" Background="#E5E5EA" Foreground="{StaticResource AppleBlue}" BorderThickness="0" Minimum="0" Maximum="100" Value="0" Margin="0,10,0,0"/>
          </StackPanel>
        </Grid>
      </Grid>
    </Border>

    <!-- 中部:左侧导航 + 右侧内容 -->
    <Grid Grid.Row="2">
      <Grid.ColumnDefinitions>
        <ColumnDefinition Width="220"/>
        <ColumnDefinition Width="*"/>
      </Grid.ColumnDefinitions>

      <!-- 左侧列表式导航 -->
      <Border Grid.Column="0" Background="{StaticResource BgSidebar}" BorderBrush="{StaticResource BdLine}" BorderThickness="0,0,1,0">
        <ScrollViewer VerticalScrollBarVisibility="Auto" Padding="14,18">
          <StackPanel>
            <TextBlock Text="主要操作" Style="{StaticResource SectionTitle}" Margin="6,0,0,8"/>
            <Button x:Name="BtnRun"   Content="运行全流程"   Style="{StaticResource PrimaryBtn}" Height="36" Margin="0,0,0,6"/>
            <Button x:Name="BtnPack"  Content="打包交付"     Style="{StaticResource AuxBtn}"    Height="36" Margin="0,0,0,18"/>

            <TextBlock Text="辅助操作" Style="{StaticResource SectionTitle}" Margin="6,0,0,8"/>
            <Button x:Name="BtnOpenOut"   Content="打开 output 目录"  Style="{StaticResource NavItem}" Height="36" Margin="0,0,0,2"/>
            <Button x:Name="BtnOpenCfg"   Content="打开配置编辑器"    Style="{StaticResource NavItem}" Height="36" Margin="0,0,0,2"/>
            <Button x:Name="BtnOpenBoard" Content="打开最新看板"      Style="{StaticResource NavItem}" Height="36" Margin="0,0,0,2"/>
            <Button x:Name="BtnRefresh"   Content="刷新状态卡"        Style="{StaticResource NavItem}" Height="36" Margin="0,0,0,18"/>

            <TextBlock Text="视图" Style="{StaticResource SectionTitle}" Margin="6,0,0,8"/>
            <Button x:Name="BtnSwitchLog"   Content="日志输出"  Style="{StaticResource NavItem}" Height="36" Margin="0,0,0,2"/>
            <Button x:Name="BtnSwitchList"  Content="数据清单"  Style="{StaticResource NavItem}" Height="36" Margin="0,0,0,2"/>
            <Button x:Name="BtnSwitchHelp"  Content="快速说明"  Style="{StaticResource NavItem}" Height="36" Margin="0,0,0,2"/>
            <Button x:Name="BtnSwitchFAQ"   Content="常见问题"  Style="{StaticResource NavItem}" Height="36" Margin="0,0,0,18"/>

            <Button x:Name="BtnExit" Content="退出" Style="{StaticResource NavItem}" Foreground="{StaticResource AppleRed}" Height="36" Margin="0,12,0,0"/>
          </StackPanel>
        </ScrollViewer>
      </Border>

      <!-- 右侧主区 -->
      <Grid Grid.Column="1" Background="{StaticResource BgPage}">
        <Grid.RowDefinitions>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="*"/>
        </Grid.RowDefinitions>

        <!-- iOS 分段控件 -->
        <Grid Grid.Row="0" Margin="20,18,20,12">
          <Border Background="{StaticResource SegBg}" CornerRadius="9" Padding="3" HorizontalAlignment="Left">
            <StackPanel Orientation="Horizontal" x:Name="Segmented">
              <Button x:Name="SegLog"  Content="日志输出" Style="{StaticResource SegBtn}" Background="{StaticResource SegFg}" Foreground="{StaticResource AppleBlue}" Height="32" FontWeight="SemiBold"/>
              <Button x:Name="SegList" Content="数据清单" Style="{StaticResource SegBtn}" Background="Transparent" Foreground="{StaticResource TxtBlack}" Height="32"/>
              <Button x:Name="SegHelp" Content="快速说明" Style="{StaticResource SegBtn}" Background="Transparent" Foreground="{StaticResource TxtBlack}" Height="32"/>
              <Button x:Name="SegFAQ"  Content="常见问题" Style="{StaticResource SegBtn}" Background="Transparent" Foreground="{StaticResource TxtBlack}" Height="32"/>
            </StackPanel>
          </Border>
          <Button x:Name="BtnClearLog" Content="清空日志" Style="{StaticResource AuxBtn}" Height="30" HorizontalAlignment="Right" Padding="14,0" FontSize="12"/>
        </Grid>

        <!-- 4 个页面对应 Panel,通过可见性切换 -->
        <Grid Grid.Row="1" Margin="20,0,20,20">
          <!-- 日志页 -->
          <Border x:Name="PageLog" Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="1" CornerRadius="12">
            <ScrollViewer x:Name="LogScroll" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Auto" Padding="14,12">
              <TextBox x:Name="LogBox" IsReadOnly="True" Background="Transparent" BorderThickness="0"
                       FontFamily="Cascadia Mono, Menlo, Consolas" FontSize="12.5"
                       Foreground="#1D1D1F" TextWrapping="NoWrap" AcceptsReturn="True"/>
            </ScrollViewer>
          </Border>

          <!-- 数据清单页 -->
          <ScrollViewer x:Name="PageList" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
            <StackPanel x:Name="PanelDataList">
              <TextBlock Text="原始数据" Style="{StaticResource SectionTitle}" FontSize="13" Margin="0,4,0,10"/>
              <Border Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="1" CornerRadius="12" Padding="14,10">
                <ItemsControl x:Name="ListRaw"/>
              </Border>
              <TextBlock Text="系统数据清理" Style="{StaticResource SectionTitle}" FontSize="13" Margin="0,18,0,10"/>
              <Border Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="1" CornerRadius="12" Padding="14,10">
                <ItemsControl x:Name="ListCleaned"/>
              </Border>
              <TextBlock Text="output 产物" Style="{StaticResource SectionTitle}" FontSize="13" Margin="0,18,0,10"/>
              <Border Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="1" CornerRadius="12" Padding="14,10">
                <ItemsControl x:Name="ListOutput"/>
              </Border>
              <TextBlock Text="手动维护指标" Style="{StaticResource SectionTitle}" FontSize="13" Margin="0,18,0,10"/>
              <Border Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="1" CornerRadius="12" Padding="14,10">
                <ItemsControl x:Name="ListManual"/>
              </Border>
            </StackPanel>
          </ScrollViewer>

          <!-- 快速说明页 -->
          <ScrollViewer x:Name="PageHelp" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
            <StackPanel>
              <Border Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="1" CornerRadius="12" Padding="20,16">
                <StackPanel>
                  <TextBlock Text="系统流程" FontWeight="SemiBold" FontSize="14" Foreground="{StaticResource TxtBlack}" Margin="0,0,0,8"/>
                  <TextBlock TextWrapping="Wrap" Foreground="{StaticResource TxtBlack}" LineHeight="22" FontSize="13">
                    <Run Text="1. 原始数据 (data/raw/财务端数据、运营端数据、往年收入/回款、客户名单) 经引擎清洗为 系统数据清理 (data/sheets/系统数据清理/...)"/>
                    <LineBreak/><Run Text="2. 销售引擎完成 黄浩浩/周涵林 拆分、跨父组法人等特殊规则,生成 销售收入/销售回款"/>
                    <LineBreak/><Run Text="3. 渲染层生成 6 页看板 (output/看板/看板_YYYYMMDD.html) 与数据总表 (output/数据/data_YYYYMMDD.xlsx)"/>
                    <LineBreak/><Run Text="4. 销售完成度汇总表 (output/销售完成度/销售完成度汇总_YYYYMMDD.xlsx) 由 scripts/sales_summary_report.py 生成"/>
                  </TextBlock>
                </StackPanel>
              </Border>
              <Border Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="1" CornerRadius="12" Padding="20,16" Margin="0,12,0,0">
                <StackPanel>
                  <TextBlock Text="目录速查" FontWeight="SemiBold" FontSize="14" Foreground="{StaticResource TxtBlack}" Margin="0,0,0,8"/>
                  <TextBlock TextWrapping="Wrap" Foreground="{StaticResource TxtBlack}" LineHeight="22" FontSize="13">
                    <Run Text="• data/raw/财务端数据/   收入.xlsx / 回款.xlsx / 广东公司.xlsx / 湖南公司.xlsx / 南方韶关.xlsx"/>
                    <LineBreak/><Run Text="• data/raw/运营端数据/   收入.xls / 回款.xls"/>
                    <LineBreak/><Run Text="• data/raw/往年收入数据/ 往年年收入.xlsx (基线年)"/>
                    <LineBreak/><Run Text="• data/raw/往年回款数据/ 往年年回款.xlsx"/>
                    <LineBreak/><Run Text="• data/raw/客户名单/     客户名单.xlsx (471 个标准客户)"/>
                    <LineBreak/><Run Text="• data/mappings/         部门事业部映射.json + 客户名单.json"/>
                    <LineBreak/><Run Text="• config/清洗配置/cleaning_config.json  时间范围 / 输出路径 / 列映射"/>
                    <LineBreak/><Run Text="• config/配置编辑器.xlsx  时间范围可在 Excel 中编辑,运行前自动同步到 JSON"/>
                  </TextBlock>
                </StackPanel>
              </Border>
              <Border Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="1" CornerRadius="12" Padding="20,16" Margin="0,12,0,0">
                <StackPanel>
                  <TextBlock Text="常用操作" FontWeight="SemiBold" FontSize="14" Foreground="{StaticResource TxtBlack}" Margin="0,0,0,8"/>
                  <TextBlock TextWrapping="Wrap" Foreground="{StaticResource TxtBlack}" LineHeight="22" FontSize="13">
                    <Run Text="• 改时间范围:  打开 config/配置编辑器.xlsx,修改时间范围 sheet 后点 运行全流程"/>
                    <LineBreak/><Run Text="• 改归属/拆分: config/前端渲染/客户销售归属.json + 展示规则.json"/>
                    <LineBreak/><Run Text="• 加客户:     在 config/配置编辑器.xlsx 的 客户白名单 sheet 增删"/>
                    <LineBreak/><Run Text="• 出错定位:   复制日志中 [错误] 段,提交给开发者"/>
                  </TextBlock>
                </StackPanel>
              </Border>
            </StackPanel>
          </ScrollViewer>

          <!-- 常见问题页 -->
          <ScrollViewer x:Name="PageFAQ" Visibility="Collapsed" VerticalScrollBarVisibility="Auto">
            <StackPanel>
              <Border Background="{StaticResource BgCard}" BorderBrush="{StaticResource BdLine}" BorderThickness="1" CornerRadius="12" Padding="20,16">
                <StackPanel>
                  <TextBlock Text="Q1: 双击启动系统.bat 没弹出窗口?" FontWeight="SemiBold" Foreground="{StaticResource TxtBlack}" Margin="0,0,0,6"/>
                  <TextBlock TextWrapping="Wrap" Foreground="{StaticResource TxtMuted}" LineHeight="22" FontSize="13"
                             Text="检查 PowerShell 执行策略:以管理员运行 PowerShell,执行 Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass,再重试。"/>
                  <TextBlock Text="Q2: 弹出窗口但是中文乱码?" FontWeight="SemiBold" Foreground="{StaticResource TxtBlack}" Margin="0,16,0,6"/>
                  <TextBlock TextWrapping="Wrap" Foreground="{StaticResource TxtMuted}" LineHeight="22" FontSize="13"
                             Text="控制面板 → 区域 → 管理 → 更改系统区域设置 → 勾选 Beta:使用 Unicode UTF-8 提供全球语言支持,重启后重试。"/>
                  <TextBlock Text="Q3: 提示 未找到 Python 解释器?" FontWeight="SemiBold" Foreground="{StaticResource TxtBlack}" Margin="0,16,0,6"/>
                  <TextBlock TextWrapping="Wrap" Foreground="{StaticResource TxtMuted}" LineHeight="22" FontSize="13"
                             Text="说明 runtime/python/python.exe 不在。先运行 scripts/prepare_runtime.bat 构建内置运行时,或安装 Python 3.12+ 并执行 pip install -r requirements.txt。"/>
                  <TextBlock Text="Q4: 看板数据对不上?" FontWeight="SemiBold" Foreground="{StaticResource TxtBlack}" Margin="0,16,0,6"/>
                  <TextBlock TextWrapping="Wrap" Foreground="{StaticResource TxtMuted}" LineHeight="22" FontSize="13"
                             Text="1) 检查 config/清洗配置/cleaning_config.json 中时间范围;2) 检查 data/raw 数据是否替换;3) 删除 output 与 data/sheets/系统数据清理 后重新运行全流程。"/>
                  <TextBlock Text="Q5: 如何把系统打包发给同事?" FontWeight="SemiBold" Foreground="{StaticResource TxtBlack}" Margin="0,16,0,6"/>
                  <TextBlock TextWrapping="Wrap" Foreground="{StaticResource TxtMuted}" LineHeight="22" FontSize="13"
                             Text="点击左侧 打包交付 (package)。生成的 Visual-Dashboard-System_vYYYYMMDD.zip 解压即可使用,无需安装 Python。"/>
                  <TextBlock Text="Q6: 日志提示 退出码 N (非 0)?" FontWeight="SemiBold" Foreground="{StaticResource TxtBlack}" Margin="0,16,0,6"/>
                  <TextBlock TextWrapping="Wrap" Foreground="{StaticResource TxtMuted}" LineHeight="22" FontSize="13"
                             Text="往上滚动看 [错误] 段,通常原因:原始 Excel 缺列、列名变化、JSON 损坏、磁盘空间不足。把日志发给开发者。"/>
                </StackPanel>
              </Border>
            </StackPanel>
          </ScrollViewer>
        </Grid>
      </Grid>
    </Grid>

    <!-- 底部状态栏(极简) -->
    <Border Grid.Row="3" Background="Transparent" BorderBrush="{StaticResource BdLine}" BorderThickness="0,1,0,0">
      <Grid Margin="20,0">
        <Grid.ColumnDefinitions>
          <ColumnDefinition Width="Auto"/>
          <ColumnDefinition Width="*"/>
          <ColumnDefinition Width="Auto"/>
          <ColumnDefinition Width="Auto"/>
        </Grid.ColumnDefinitions>
        <TextBlock Grid.Column="0" x:Name="LblStatus" Text="就绪 — 点击左侧按钮开始" Foreground="{StaticResource TxtMuted}" FontSize="11.5" VerticalAlignment="Center"/>
        <TextBlock Grid.Column="2" x:Name="LblElapsed" Text="耗时 00:00:00" Foreground="{StaticResource TxtMuted}" FontSize="11.5" VerticalAlignment="Center" Margin="0,0,20,0"/>
        <TextBlock Grid.Column="3" x:Name="LblExit" Text="退出码 —" Foreground="{StaticResource TxtMuted}" FontSize="11.5" VerticalAlignment="Center"/>
      </Grid>
    </Border>
  </Grid>
</Window>
'@

# ---------- 加载 XAML ----------
$reader = New-Object System.Xml.XmlNodeReader $xaml
$window = [Windows.Markup.XamlReader]::Load($reader)

# ---------- 启动加载小窗(数据预加载时显示) ----------
[xml]$splashXaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Width="420" Height="160" WindowStartupLocation="CenterScreen"
        WindowStyle="None" ResizeMode="NoResize" AllowsTransparency="True"
        Background="Transparent" ShowInTaskbar="False" Topmost="True">
  <Border Background="White" CornerRadius="10" BorderBrush="#E5E5E5" BorderThickness="1" Margin="6">
    <Border.Effect>
      <DropShadowEffect BlurRadius="16" ShadowDepth="0" Opacity="0.18"/>
    </Border.Effect>
    <Grid Margin="20">
      <Grid.RowDefinitions>
        <RowDefinition Height="Auto"/>
        <RowDefinition Height="Auto"/>
        <RowDefinition Height="Auto"/>
        <RowDefinition Height="Auto"/>
      </Grid.RowDefinitions>
      <TextBlock x:Name="SplashTitle" Grid.Row="0" Text="销售运营可视化看板系统" FontSize="14" FontWeight="Bold" Foreground="#222222"/>
      <TextBlock x:Name="SplashHint"  Grid.Row="1" Text="正在启动..." FontSize="11" Foreground="#888888" Margin="0,2,0,0"/>
      <ProgressBar x:Name="SplashBar" Grid.Row="2" Height="6" Margin="0,18,0,6" Background="#E5E5EA" Foreground="#007AFF" BorderThickness="0" Minimum="0" Maximum="100"/>
      <TextBlock x:Name="SplashStep" Grid.Row="3" Text="准备中..." FontSize="11" Foreground="#666666"/>
    </Grid>
  </Border>
</Window>
'@
$splashReader = New-Object System.Xml.XmlNodeReader $splashXaml
$splash = [Windows.Markup.XamlReader]::Load($splashReader)
$splashBar  = $splash.FindName('SplashBar')
$splashHint = $splash.FindName('SplashHint')
$splashStep = $splash.FindName('SplashStep')
Write-BootLog 'splash 显示'
[void]$splash.Show()

# 注意:不能用 PushFrame / DoEvents 驱动刷新(会死锁)。
# Preload 全程同步执行,通常 <1s;splash 只做静态占位,进度条最后一次刷新即可。
function Update-Splash {
    param([int]$pct, [string]$step)
    $splashBar.Value  = $pct
    $splashStep.Text  = $step
}

# ---------- 数据预加载(在主窗 ShowDialog 之前完成) ----------
$script:Cached = @{
    StatCards = $null
    DataList  = $null
    LoadedAt  = $null
}

function Preload-CachedData {
    $script:Cached.LoadedAt = Get-Date
    Update-Splash 15 '加载配置(cleaning_config.json)'
    $cfgPath = Join-Path $script:BaseDir 'config\清洗配置\cleaning_config.json'
    $cfg = $null
    if (Test-Path $cfgPath) {
        try { $cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $cfg = $null }
    }
    $script:Cached.StatCards = @{
        Year    = if ($cfg -and $cfg.'时间范围'.'年度累计') { $cfg.'时间范围'.'年度累计'.start_date + ' ~ ' + ($cfg.'时间范围'.'年度累计'.end_date -replace ' 23:59:59','') } else { '—' }
        YearHint= if ($cfg -and $cfg.'时间范围'.'年度累计') { $cfg.'时间范围'.'年度累计'.'_使用方' } else { '配置文件不存在' }
        Month   = if ($cfg -and $cfg.'时间范围'.'月度数据') { $cfg.'时间范围'.'月度数据'.start_date + ' ~ ' + ($cfg.'时间范围'.'月度数据'.end_date -replace ' 23:59:59','') } else { '—' }
        MonthHint=if ($cfg -and $cfg.'时间范围'.'月度数据') { $cfg.'时间范围'.'月度数据'.'_使用方' } else { '' }
        Mode    = if ($cfg -and $cfg.'时间范围'.'结算模式') { $cfg.'时间范围'.'结算模式'.'值' } else { '—' }
        ModeHint= if ($cfg -and $cfg.'时间范围'.'结算模式') {
                      $h = $cfg.'时间范围'.'结算模式'.'_说明'
                      if ($h.Length -gt 38) { $h = $h.Substring(0,38) + '…' }
                      $h
                  } else { '' }
    }
    Update-Splash 40 '扫描原始数据 (data/raw)'
    $rawRows = @()
    foreach ($p in @(
        @{ n='财务端·收入';  p='data\raw\财务端数据\收入.xlsx' },
        @{ n='财务端·回款';  p='data\raw\财务端数据\回款.xlsx' },
        @{ n='广东公司';     p='data\raw\财务端数据\广东公司.xlsx' },
        @{ n='湖南公司';     p='data\raw\财务端数据\湖南公司.xlsx' },
        @{ n='南方韶关';     p='data\raw\财务端数据\南方韶关.xlsx' },
        @{ n='运营端·收入';  p='data\raw\运营端数据\收入.xls' },
        @{ n='运营端·回款';  p='data\raw\运营端数据\回款.xls' },
        @{ n='往年收入';     p='data\raw\往年收入数据\往年年收入.xlsx' },
        @{ n='往年回款';     p='data\raw\往年回款数据\往年年回款.xlsx' },
        @{ n='客户名单';     p='data\raw\客户名单\客户名单.xlsx' }
    )) {
        $full = Join-Path $script:BaseDir $p.p
        $rawRows += [pscustomobject]@{ Name=$p.n; Path=$full; Exists=(Test-Path $full) }
    }
    Update-Splash 60 '扫描清洗产物 (系统数据清理)'
    $cleanRows = @()
    foreach ($n in @('月收入','月回款','当年累计收入','当年累计回款','季度累计收入','季度累计回款','销售收入','销售回款','往年收入','往年回款')) {
        $full = Join-Path $script:BaseDir "data\sheets\系统数据清理\$n"
        $cnt = 0
        if (Test-Path $full) { $cnt = (Get-ChildItem $full -File -ErrorAction SilentlyContinue | Measure-Object).Count }
        $cleanRows += [pscustomobject]@{ Name="$n  ($cnt 个文件)"; Path=$full; Exists=(Test-Path $full) }
    }
    Update-Splash 80 '扫描 output 产物'
    $outRows = @()
    foreach ($p in @(
        @{ n='看板';       p='output\看板' },
        @{ n='数据总表';    p='output\数据' },
        @{ n='销售完成度';  p='output\销售完成度' }
    )) {
        $full = Join-Path $script:BaseDir $p.p
        $latest = $null
        if (Test-Path $full) {
            $latest = Get-ChildItem $full -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        }
        $label = if ($latest) { "$($p.n)  ·  最近: $($latest.Name)" } else { "$($p.n)  ·  (空)" }
        $outRows += [pscustomobject]@{ Name=$label; Path=$full; Exists=($null -ne $latest) }
    }
    Update-Splash 90 '扫描手动维护指标'
    $manRows = @()
    foreach ($n in @('年度收入总指标','年度回款总指标','季度收入指标','季度回款指标','月度收入指标','月度回款指标')) {
        $full = Join-Path $script:BaseDir "data\sheets\手动维护\$n"
        $manRows += [pscustomobject]@{ Name=$n; Path=$full; Exists=(Test-Path $full) }
    }

    # 最近产物
    $lastBoard = $null; $lastData = $null
    $boardDir = Join-Path $script:BaseDir 'output\看板'
    $dataDir  = Join-Path $script:BaseDir 'output\数据'
    if (Test-Path $boardDir) { $lastBoard = Get-ChildItem $boardDir -Filter '看板_*.html' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 }
    if (Test-Path $dataDir)  { $lastData  = Get-ChildItem $dataDir  -Filter 'data_*.xlsx' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 }
    $latest = $null
    if ($lastBoard -and $lastData) {
        $latest = if ($lastBoard.LastWriteTime -gt $lastData.LastWriteTime) { $lastBoard } else { $lastData }
    } else { $latest = $lastBoard; if (-not $latest) { $latest = $lastData } }
    $script:Cached.StatCards.Latest     = if ($latest) { $latest.Name } else { '—' }
    $script:Cached.StatCards.LatestHint = if ($latest) { '生成于 ' + $latest.LastWriteTime.ToString('yyyy-MM-dd HH:mm') } else { '运行全流程后生成' }
    $script:Cached.DataList = @{
        Raw     = $rawRows
        Cleaned = $cleanRows
        Output  = $outRows
        Manual  = $manRows
    }
    Update-Splash 100 '加载完成'
    Start-Sleep -Milliseconds 250  # 让用户看到 100% 一闪
}

# 立即预加载(主窗 ShowDialog 之前)
Preload-CachedData
Write-BootLog 'preload 完成'
$splash.Close()
Write-BootLog 'splash 关闭'

# ---------- 绑定控件(必须在 Preload 之后:UI 控件已存在,才能写入数据) ----------
$controls = @{
    Window         = $window
    DotHeader      = $window.FindName('DotHeader')
    LblHeaderStatus= $window.FindName('LblHeaderStatus')
    LblStatYear    = $window.FindName('LblStatYear')
    LblStatYearHint= $window.FindName('LblStatYearHint')
    LblStatMonth   = $window.FindName('LblStatMonth')
    LblStatMonthHint=$window.FindName('LblStatMonthHint')
    LblStatMode    = $window.FindName('LblStatMode')
    LblStatModeHint= $window.FindName('LblStatModeHint')
    LblStatLatest  = $window.FindName('LblStatLatest')
    LblStatLatestHint=$window.FindName('LblStatLatestHint')
    PhasePanel     = $window.FindName('PhasePanel')
    PhaseProgress  = $window.FindName('PhaseProgress')
    LblPhaseText   = $window.FindName('LblPhaseText')
    BtnRun         = $window.FindName('BtnRun')
    BtnPack        = $window.FindName('BtnPack')
    BtnOpenOut     = $window.FindName('BtnOpenOut')
    BtnOpenCfg     = $window.FindName('BtnOpenCfg')
    BtnOpenBoard   = $window.FindName('BtnOpenBoard')
    BtnRefresh     = $window.FindName('BtnRefresh')
    BtnExit        = $window.FindName('BtnExit')
    BtnClearLog    = $window.FindName('BtnClearLog')
    LogBox         = $window.FindName('LogBox')
    LogScroll      = $window.FindName('LogScroll')
    SegLog         = $window.FindName('SegLog')
    SegList        = $window.FindName('SegList')
    SegHelp        = $window.FindName('SegHelp')
    SegFAQ         = $window.FindName('SegFAQ')
    BtnSwitchLog   = $window.FindName('BtnSwitchLog')
    BtnSwitchList  = $window.FindName('BtnSwitchList')
    BtnSwitchHelp  = $window.FindName('BtnSwitchHelp')
    BtnSwitchFAQ   = $window.FindName('BtnSwitchFAQ')
    PageLog        = $window.FindName('PageLog')
    PageList       = $window.FindName('PageList')
    PageHelp       = $window.FindName('PageHelp')
    PageFAQ        = $window.FindName('PageFAQ')
    PanelDataList  = $window.FindName('PanelDataList')
    ListRaw        = $window.FindName('ListRaw')
    ListCleaned    = $window.FindName('ListCleaned')
    ListOutput     = $window.FindName('ListOutput')
    ListManual     = $window.FindName('ListManual')
    LblStatus      = $window.FindName('LblStatus')
    LblElapsed     = $window.FindName('LblElapsed')
    LblExit        = $window.FindName('LblExit')
}

# ---------- Segmented 控件 + 页面切换 ----------
function Set-SegStyle($seg, $active) {
    if ($active) {
        $seg.Background = WColor('#FFFFFF')
        $seg.Foreground = WColor('#007AFF')
    } else {
        $seg.Background = [System.Windows.Media.Brushes]::Transparent
        $seg.Foreground = WColor('#1D1D1F')
    }
}
function Switch-Page($which) {
    $controls.PageLog.Visibility  = if ($which -eq 'log')  { 'Visible' } else { 'Collapsed' }
    $controls.PageList.Visibility = if ($which -eq 'list') { 'Visible' } else { 'Collapsed' }
    $controls.PageHelp.Visibility = if ($which -eq 'help') { 'Visible' } else { 'Collapsed' }
    $controls.PageFAQ.Visibility  = if ($which -eq 'faq')  { 'Visible' } else { 'Collapsed' }
    Set-SegStyle $controls.SegLog  ($which -eq 'log')
    Set-SegStyle $controls.SegList ($which -eq 'list')
    Set-SegStyle $controls.SegHelp ($which -eq 'help')
    Set-SegStyle $controls.SegFAQ  ($which -eq 'faq')
}
$controls.SegLog.add_Click(        { Switch-Page 'log' })
$controls.SegList.add_Click(       { Switch-Page 'list' })
$controls.SegHelp.add_Click(       { Switch-Page 'help' })
$controls.SegFAQ.add_Click(        { Switch-Page 'faq' })
$controls.BtnSwitchLog.add_Click(  { Switch-Page 'log' })
$controls.BtnSwitchList.add_Click( { Switch-Page 'list' })
$controls.BtnSwitchHelp.add_Click( { Switch-Page 'help' })
$controls.BtnSwitchFAQ.add_Click(  { Switch-Page 'faq' })

# ---------- 阶段定义(供步骤进度 + 进度识别) ----------
$script:Phases = @(
    @{ Name='预检';         Pattern='═══ 预检 ═══';                       DonePattern='✅';           Weight=1 },
    @{ Name='配置同步';      Pattern='═══ 配置同步 ═══';                    DonePattern='\[跳过\]|\[系统\]'; Weight=1 },
    @{ Name='年基线清洗';    Pattern='═══ Phase 0: 年基线清洗 ═══';        DonePattern='Phase 1\+2';     Weight=1 },
    @{ Name='收入/回款清洗'; Pattern='═══ Phase 1\+2: 收入/回款清洗 ═══'; DonePattern='Phase 3';        Weight=2 },
    @{ Name='销售拆分';      Pattern='═══ Phase 3: 销售拆分 ═══';          DonePattern='Phase 4';        Weight=2 },
    @{ Name='渲染看板';      Pattern='═══ Phase 4: 渲染看板';              DonePattern='Phase 5|生成销售完成度'; Weight=2 },
    @{ Name='汇总与验证';    Pattern='═══ Phase 5|Phase 6|全部完成';        DonePattern='✅ 全部完成';     Weight=1 }
)

# ---------- 动态生成阶段 chip ----------
function New-PhaseChip {
    param($name, $index)
    $border = New-Object System.Windows.Controls.Border
    $border.CornerRadius = [System.Windows.CornerRadius]::new(12)
    $border.Padding = [System.Windows.Thickness]::new(10,4,10,4)
    $border.Margin = [System.Windows.Thickness]::new(0,0,8,0)
    $border.Background = [System.Windows.Media.Brushes]::LightGray
    $border.Tag = 'pending'

    $tb = New-Object System.Windows.Controls.TextBlock
    $tb.Text = "$($index+1). $name"
    $tb.FontSize = 11.5
    $tb.Foreground = [System.Windows.Media.Brushes]::Gray
    $tb.FontWeight = 'Bold'
    $border.Child = $tb

    # 用 Child 的 Tag 记录阶段索引
    $script:PhaseChips[$index] = @{ Border=$border; Tb=$tb; Name=$name }
    return $border
}

$script:PhaseChips = @{}
$phaseRow = New-Object System.Windows.Controls.StackPanel
$phaseRow.Orientation = 'Horizontal'
for ($i=0; $i -lt $script:Phases.Count; $i++) {
    $chip = New-PhaseChip -name $script:Phases[$i].Name -index $i
    [void]$phaseRow.Children.Add($chip)
}
[void]$controls.PhasePanel.Children.Add($phaseRow)

# ---------- 状态 ----------
$script:proc     = $null
$script:queue    = New-Object 'System.Collections.Concurrent.ConcurrentQueue[string]'
$script:busy     = $false
$script:done     = $false
$script:lastCode = $null
$script:startTs  = $null
$script:currentPhase = -1  # -1=未运行

# ---------- 配色函数(转 System.Windows.Media 颜色) ----------
function WColor($hex) {
    $c = [System.Windows.Media.ColorConverter]::ConvertFromString($hex)
    return New-Object System.Windows.Media.SolidColorBrush $c
}

# ---------- 刷新状态卡 ----------
function Refresh-StatCards {
    $c = $script:Cached.StatCards
    if (-not $c) { return }
    $controls.LblStatYear.Text     = $c.Year
    $controls.LblStatYearHint.Text = $c.YearHint
    $controls.LblStatMonth.Text    = $c.Month
    $controls.LblStatMonthHint.Text= $c.MonthHint
    $controls.LblStatMode.Text     = $c.Mode
    $controls.LblStatModeHint.Text = $c.ModeHint
    $controls.LblStatLatest.Text   = $c.Latest
    $controls.LblStatLatestHint.Text = $c.LatestHint
}

# ---------- 刷新数据清单 ----------
function New-FileRow {
    param($label, $path, $hint)
    $sp = New-Object System.Windows.Controls.StackPanel
    $sp.Orientation = 'Horizontal'
    $sp.Margin = [System.Windows.Thickness]::new(0,2,0,2)

    $dot = New-Object System.Windows.Controls.Border
    $dot.Width = 8; $dot.Height = 8
    $dot.CornerRadius = [System.Windows.CornerRadius]::new(4)
    $dot.VerticalAlignment = 'Center'
    $ok = Test-Path $path
    $dot.Background = if ($ok) { WColor('#34C759') } else { WColor('#FF3B30') }
    $dot.Margin = [System.Windows.Thickness]::new(0,0,8,0)

    $txt = New-Object System.Windows.Controls.TextBlock
    $txt.Text = "$label  "
    $txt.FontSize = 12.5
    $txt.Foreground = WColor('#333333')
    $txt.VerticalAlignment = 'Center'

    $pathTb = New-Object System.Windows.Controls.TextBlock
    $pathTb.Text = $path.Replace($script:BaseDir, '.')
    $pathTb.FontSize = 11
    $pathTb.FontFamily = 'Cascadia Mono, Consolas'
    $pathTb.Foreground = WColor('#888888')
    $pathTb.VerticalAlignment = 'Center'

    $sp.Children.Add($dot) | Out-Null
    $sp.Children.Add($txt) | Out-Null
    $sp.Children.Add($pathTb) | Out-Null
    return $sp
}

function Refresh-DataList {
    $controls.ListRaw.Items.Clear()
    $controls.ListCleaned.Items.Clear()
    $controls.ListOutput.Items.Clear()
    $controls.ListManual.Items.Clear()

    # 优先用缓存(预加载阶段已扫描完毕,ShowDialog 后立即显示)
    $dl = $script:Cached.DataList
    if ($dl) {
        foreach ($r in $dl.Raw)     { $controls.ListRaw.Items.Add((New-FileRow -label $r.Name -path $r.Path))     | Out-Null }
        foreach ($r in $dl.Cleaned) { $controls.ListCleaned.Items.Add((New-FileRow -label $r.Name -path $r.Path)) | Out-Null }
        foreach ($r in $dl.Output)  { $controls.ListOutput.Items.Add((New-FileRow -label $r.Name -path $r.Path))  | Out-Null }
        foreach ($r in $dl.Manual)  { $controls.ListManual.Items.Add((New-FileRow -label $r.Name -path $r.Path))  | Out-Null }
        return
    }

    # raw
    $rawBase = Join-Path $script:BaseDir 'data\raw'
    foreach ($p in @(
        @{ n='财务端·收入';  p='data\raw\财务端数据\收入.xlsx' },
        @{ n='财务端·回款';  p='data\raw\财务端数据\回款.xlsx' },
        @{ n='广东公司';     p='data\raw\财务端数据\广东公司.xlsx' },
        @{ n='湖南公司';     p='data\raw\财务端数据\湖南公司.xlsx' },
        @{ n='南方韶关';     p='data\raw\财务端数据\南方韶关.xlsx' },
        @{ n='运营端·收入';  p='data\raw\运营端数据\收入.xls' },
        @{ n='运营端·回款';  p='data\raw\运营端数据\回款.xls' },
        @{ n='往年收入';     p='data\raw\往年收入数据\往年年收入.xlsx' },
        @{ n='往年回款';     p='data\raw\往年回款数据\往年年回款.xlsx' },
        @{ n='客户名单';     p='data\raw\客户名单\客户名单.xlsx' }
    )) {
        $row = New-FileRow -label $p.n -path (Join-Path $script:BaseDir $p.p)
        $controls.ListRaw.Items.Add($row) | Out-Null
    }

    # cleaned(运行后才有)
    $cleanBase = Join-Path $script:BaseDir 'data\sheets\系统数据清理'
    foreach ($p in @(
        '月收入','月回款','当年累计收入','当年累计回款','季度累计收入','季度累计回款','销售收入','销售回款','往年收入','往年回款'
    )) {
        $full = Join-Path $cleanBase $p
        $count = 0
        if (Test-Path $full) {
            $count = (Get-ChildItem $full -File -ErrorAction SilentlyContinue | Measure-Object).Count
        }
        $label = "$p  ($count 个文件)"
        $row = New-FileRow -label $label -path $full -hint $count
        $controls.ListCleaned.Items.Add($row) | Out-Null
    }

    # output
    $outBase = Join-Path $script:BaseDir 'output'
    foreach ($p in @(
        @{ n='看板';       p='output\看板' },
        @{ n='数据总表';    p='output\数据' },
        @{ n='销售完成度';  p='output\销售完成度' }
    )) {
        $full = Join-Path $outBase $p.p
        $latest = $null
        if (Test-Path $full) {
            $latest = Get-ChildItem $full -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        }
        $label = if ($latest) { "$($p.n)  ·  最近: $($latest.Name)" } else { "$($p.n)  ·  (空)" }
        $row = New-FileRow -label $label -path $full
        $controls.ListOutput.Items.Add($row) | Out-Null
    }

    # manual
    foreach ($p in @(
        '年度收入总指标','年度回款总指标','季度收入指标','季度回款指标','月度收入指标','月度回款指标'
    )) {
        $full = Join-Path $script:BaseDir "data\sheets\手动维护\$p"
        $row = New-FileRow -label $p -path $full
        $controls.ListManual.Items.Add($row) | Out-Null
    }
}

# ---------- 阶段状态更新 ----------
function Update-PhaseChip {
    param($index, $status)  # status: pending | running | done | failed
    if ($index -lt 0 -or $index -ge $script:Phases.Count) { return }
    $chip = $script:PhaseChips[$index]
    switch ($status) {
        'pending' {
            $chip.Border.Background = WColor('#E5E5EA')
            $chip.Tb.Foreground = WColor('#86868B')
        }
        'running' {
            $chip.Border.Background = WColor('#007AFF')
            $chip.Tb.Foreground = [System.Windows.Media.Brushes]::White
        }
        'done' {
            $chip.Border.Background = WColor('#E5F1FF')
            $chip.Tb.Foreground = WColor('#007AFF')
        }
        'failed' {
            $chip.Border.Background = WColor('#FFE5E3')
            $chip.Tb.Foreground = WColor('#FF3B30')
        }
    }
}

function Set-AllPhasesPending {
    for ($i=0; $i -lt $script:Phases.Count; $i++) { Update-PhaseChip $i 'pending' }
}

function Compute-TotalWeight {
    $s = 0
    foreach ($p in $script:Phases) { $s += $p.Weight }
    return $s
}

function Compute-Progress {
    $total = Compute-TotalWeight
    $done = 0
    for ($i=0; $i -lt $script:Phases.Count; $i++) {
        if ($script:PhaseChips[$i].Border.Tag -eq 'done') { $done += $script:Phases[$i].Weight }
        elseif ($script:PhaseChips[$i].Border.Tag -eq 'running') { $done += $script:Phases[$i].Weight * 0.5 }
    }
    return [int]($done / $total * 100)
}

function Update-PhaseTextLabel {
    if (-not $controls.LblPhaseText) { return }
    if ($script:currentPhase -lt 0) {
        $controls.LblPhaseText.Text = "第 0 / $($script:Phases.Count) 阶段"
        return
    }
    $doneCount = 0
    for ($i=0; $i -lt $script:currentPhase; $i++) {
        if ($script:PhaseStatus[$i] -eq 'done') { $doneCount++ }
    }
    $controls.LblPhaseText.Text = "第 $($script:currentPhase+1) / $($script:Phases.Count) 阶段"
}

# 给 Border 额外加个 Tag 属性存状态(避免和现有 Tag 冲突,用脚本映射)
$script:PhaseStatus = @{}  # index -> status
for ($i=0; $i -lt $script:Phases.Count; $i++) { $script:PhaseStatus[$i] = 'pending' }

function Update-PhaseChip2 {
    param($index, $status)
    $script:PhaseStatus[$index] = $status
    Update-PhaseChip $index $status
}

# ---------- 阶段识别(扫描日志行) ----------
function Detect-Phase($line) {
    if ($script:currentPhase -ge 0 -and $script:PhaseStatus[$script:currentPhase] -ne 'done') {
        # 看是否走到了当前阶段的结束 pattern
        $cur = $script:Phases[$script:currentPhase]
        if ($cur.DonePattern -and ($line -match $cur.DonePattern)) {
            Update-PhaseChip2 $script:currentPhase 'done'
            $controls.PhaseProgress.Value = Compute-Progress
            Update-PhaseTextLabel
        }
    }
    # 找下一个未完成的阶段(用 Pattern 匹配)
    for ($i=0; $i -lt $script:Phases.Count; $i++) {
        $p = $script:Phases[$i]
        if ($script:PhaseStatus[$i] -eq 'pending' -and $line -match [regex]::Escape($p.Pattern)) {
            Update-PhaseChip2 $i 'running'
            $script:currentPhase = $i
            $controls.PhaseProgress.Value = Compute-Progress
            Update-PhaseTextLabel
            return
        }
    }
}

# ---------- 日志 ----------
function Write-Log([string]$msg) {
    $ts = (Get-Date).ToString('HH:mm:ss')
    $controls.LogBox.AppendText("[$ts] $msg`r`n")
    $controls.LogScroll.ScrollToEnd()
    if ($controls.LogBox.Text.Length -gt 300000) {
        $controls.LogBox.Text = $controls.LogBox.Text.Substring($controls.LogBox.Text.Length - 150000)
        $controls.LogBox.CaretIndex = $controls.LogBox.Text.Length
    }
}

# ---------- Busy 状态 ----------
function Set-Busy($busy) {
    $script:busy = $busy
    # null 防御 + WPF 属性名是 IsEnabled(不是 WinForms 的 Enabled)
    if ($controls.BtnRun)     { $controls.BtnRun.IsEnabled     = -not $busy }
    if ($controls.BtnPack)    { $controls.BtnPack.IsEnabled    = -not $busy }
    if ($controls.BtnRefresh) { $controls.BtnRefresh.IsEnabled = -not $busy }
    if ($busy) {
        $controls.LblStatus.Text       = '运行中…'
        $controls.LblStatus.Foreground = WColor('#FF9500')
        $controls.LblHeaderStatus.Text = '运行中'
        $controls.DotHeader.Fill       = WColor('#FF9500')
        $script:startTs = Get-Date
    } else {
        $ok = ($script:lastCode -eq 0)
        $controls.LblStatus.Foreground = if ($ok) { WColor('#34C759') } else { WColor('#FF3B30') }
        $controls.LblStatus.Text       = if ($ok) { '完成' } else { '失败' }
        $controls.LblHeaderStatus.Text = if ($ok) { '就绪' } else { '失败' }
        $controls.DotHeader.Fill       = if ($ok) { WColor('#34C759') } else { WColor('#FF3B30') }
        # 运行完成/失败后:重算缓存(新看板/数据/产物)
        Preload-CachedData
        Refresh-StatCards
        Refresh-DataList
    }
}

# ---------- 启动 bat ----------
# 关键设计:cmd 的 stdout/stderr 重定向到文件,UI 定时器增量读文件。
# 绝不使用 Process 异步输出事件(OutputDataReceived 在后台线程触发 PS 脚本块,
# 会因 runspace 忙抛 PSInvalidOperation 导致 powershell.exe 崩溃闪退)。
function Invoke-Bat($title, $batName) {
    if ($script:busy) { Write-Log '【警告】已有任务在运行,请等待完成后再试。'; return }
    $script:proc = $null
    $script:done = $false
    $script:lastCode = $null
    $script:pipeLen = 0
    $controls.LblExit.Text = '退出码: —'
    $controls.LblElapsed.Text = '耗时: 00:00:00'
    $controls.LogBox.Text = ''
    $script:currentPhase = -1
    for ($i=0; $i -lt $script:Phases.Count; $i++) {
        Update-PhaseChip2 $i 'pending'
        $script:PhaseChips[$i].Border.Tag = 'pending'
    }
    $controls.PhaseProgress.Value = 0
    Write-Log "===== $title ====="
    Write-Log "工作目录: $script:BaseDir"
    Write-Log "执行: cmd /c $batName"
    Set-Busy $true

    $bat = Join-Path $script:BaseDir $batName
    $pipeFile = Join-Path $script:BaseDir 'logs\_run_pipe.log'
    $script:pipeFile = $pipeFile
    if (Test-Path $pipeFile) { Remove-Item $pipeFile -Force }

    # 生成全 ASCII 的包装 bat(放在 BaseDir,WorkingDirectory 同目录,内容只用相对路径)
    # 不预先 chcp(目标 bat 自己管理代码页,避免解码错乱);重定向放 bat 内部
    $runner = Join-Path $script:BaseDir '_run_current.bat'
    $runnerText = "@echo off`r`ncall `"$batName`" > `"logs\_run_pipe.log`" 2>&1`r`nexit /b %errorlevel%`r`n"
    [IO.File]::WriteAllText($runner, $runnerText, [Text.Encoding]::ASCII)
    $script:runnerFile = $runner

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'cmd.exe'
    $psi.Arguments = '/d /c ""' + $runner + '""'
    $psi.WorkingDirectory = $script:BaseDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardInput = $true   # 提供 EOF,让 bat 内 pause 自动跳过
    $psi.EnvironmentVariables['PYTHONUTF8'] = '1'
    $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'

    $p = [System.Diagnostics.Process]::Start($psi)
    $p.StandardInput.Close()
    $script:proc = $p
}

# 增量读取管道文件(UTF-8),返回新增文本
function Read-PipeTail {
    if (-not $script:pipeFile) { return '' }
    if (-not (Test-Path $script:pipeFile)) { return '' }
    if (-not $script:pipeLen) { $script:pipeLen = 0 }
    try {
        $fs = [IO.File]::Open($script:pipeFile, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
        try {
            $len = $fs.Length
            if ($len -le $script:pipeLen) { return '' }
            $fs.Seek($script:pipeLen, [IO.SeekOrigin]::Begin) | Out-Null
            $sr = New-Object IO.StreamReader($fs, [Text.Encoding]::UTF8)
            $new = $sr.ReadToEnd()
            $script:pipeLen = $fs.Length
            return $new
        } finally { $fs.Dispose() }
    } catch { return '' }
}

# 把新增文本按行送入日志 + 阶段识别
function Drain-PipeLog {
    $tail = Read-PipeTail
    if (-not $tail) { return $false }
    $hasNew = $false
    $tail -split "`r?`n" | ForEach-Object {
        $l = $_
        if ($l) {
            $controls.LogBox.AppendText("$l`r`n")
            Detect-Phase $l
            $hasNew = $true
        }
    }
    if ($hasNew) { $controls.LogScroll.ScrollToEnd() }
    return $true
}

# ---------- DispatcherTimer(WPF 替代 WinForms Timer) ----------
$timer = New-Object System.Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromMilliseconds(120)
$timer.add_Tick({
    if ($script:startTs) {
        $e = (Get-Date) - $script:startTs
        $ts = '{0:00}:{1:00}:{2:00}' -f [int]$e.TotalHours, $e.Minutes, $e.Seconds
        $controls.LblElapsed.Text = "耗时: $ts"
    }
    # 从管道文件增量读取子进程输出(全程在 UI 线程,无后台线程回调)
    [void](Drain-PipeLog)
    if ($script:proc -and -not $script:done -and $script:proc.HasExited) {
        $script:done = $true
        try { $script:proc.WaitForExit() } catch { }
        $script:lastCode = $script:proc.ExitCode
        # 读完最后残留输出
        [void](Drain-PipeLog)
        if ($script:lastCode -eq 0) {
            Write-Log "===== 全部完成 ✓ 退出码 0 ====="
            # 把所有未完成的阶段标记为 done
            for ($i=0; $i -lt $script:Phases.Count; $i++) {
                if ($script:PhaseStatus[$i] -ne 'done') { Update-PhaseChip2 $i 'done' }
            }
            $controls.PhaseProgress.Value = 100
            if ($controls.LblPhaseText) { $controls.LblPhaseText.Text = "完成 · $($script:Phases.Count) / $($script:Phases.Count)" }
        } else {
            Write-Log "===== 退出码 $($script:lastCode)(非 0,请查看上方日志)====="
            # 把当前正在运行的阶段标记为失败
            if ($script:currentPhase -ge 0) { Update-PhaseChip2 $script:currentPhase 'failed' }
        }
        $controls.LblExit.Text = "退出码: $($script:lastCode)"
        $script:proc = $null
        # 清理临时 runner
        if ($script:runnerFile -and (Test-Path $script:runnerFile)) { try { Remove-Item $script:runnerFile -Force -ErrorAction SilentlyContinue } catch { } }
        Set-Busy $false
    }
})
$timer.Start()  # WPF DispatcherTimer 需要显式 Start(不是 WinForms Timer.Enabled)

# ---------- 事件绑定 ----------
$controls.BtnRun.add_Click({    Invoke-Bat '运行全流程 (run_all.bat)' 'run_all.bat' })
$controls.BtnPack.add_Click({   Invoke-Bat '打包交付 (package.bat)' 'package.bat' })
$controls.BtnRefresh.add_Click({
    # 用户主动刷新:强制重算 + 重扫(忽略缓存)
    Preload-CachedData
    Refresh-StatCards
    Refresh-DataList
    Write-Log '已刷新状态卡与数据清单。'
})
$controls.BtnClearLog.add_Click({ $controls.LogBox.Text = '' })
$controls.BtnExit.add_Click({ $window.Close() })
$controls.BtnOpenOut.add_Click({
    if ($script:busy) { return }
    $out = Join-Path $script:BaseDir 'output'
    if (Test-Path $out) { [System.Diagnostics.Process]::Start('explorer.exe', $out) | Out-Null }
    else { Write-Log "output 目录不存在: $out" }
})
$controls.BtnOpenCfg.add_Click({
    $p = Join-Path $script:BaseDir 'config\配置编辑器.xlsx'
    if (Test-Path $p) { [System.Diagnostics.Process]::Start($p) | Out-Null }
    else { Write-Log "配置编辑器不存在: $p" }
})
$controls.BtnOpenBoard.add_Click({
    $dir = Join-Path $script:BaseDir 'output\看板'
    if (Test-Path $dir) {
        $f = Get-ChildItem $dir -Filter '看板_*.html' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($f) { [System.Diagnostics.Process]::Start($f.FullName) | Out-Null; Write-Log "打开看板: $($f.Name)" }
        else { Write-Log 'output\看板 下暂无看板文件,请先运行全流程。' }
    } else { Write-Log 'output\看板 目录不存在,请先运行全流程。' }
})

# WPF Window 没有 Shown 事件(那是 WinForms),首次显示用 ContentRendered
$window.add_ContentRendered({
    # 数据已在 ShowDialog 之前写入,这里只补日志 + 焦点
    Write-Log '欢迎使用 Visual Dashboard System。'
    Write-Log "项目目录: $script:BaseDir"
    Write-Log '点击左侧按钮开始(运行全流程 / 打包交付),或辅助操作打开配置。'
    $controls.BtnRun.Focus()
})
$window.add_Closing({
    if ($script:busy -and $script:proc -and -not $script:proc.HasExited) {
        try { $script:proc.Kill() } catch { }
    }
})

# ---------- 主入口 ----------
try {
    Write-BootLog '进入 ShowDialog'
    # ShowDialog 之前:把缓存数据立刻写入 UI 控件(所有函数此时已定义完毕)
    Refresh-StatCards
    Refresh-DataList
    Update-PhaseTextLabel
    Switch-Page 'log'
    [void]$window.ShowDialog()
    Write-BootLog 'ShowDialog 正常返回'
} catch {
    $err = $_.Exception.ToString()
    $errFile = Join-Path $script:BaseDir 'logs\launcher_error.log'
    $stack = $_.ScriptStackTrace
    try { Add-Content -Path $errFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $err`n$stack" -Encoding UTF8 } catch { }
    # 不弹 MessageBox(MessageBox 本身在异常状态下会触发 AutomationException 二次崩)
    Write-Host "启动器发生错误: $err"
    Write-Host $stack
    exit 1
}
