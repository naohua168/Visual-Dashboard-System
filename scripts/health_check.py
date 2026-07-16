"""mappings健康度检查"""
import json
import os

mappings_dir = 'data/mappings'
print('=' * 60)
print('mappings/ 健康度检查')
print('=' * 60)

folders = sorted(os.listdir(mappings_dir))
print('\n文件夹数: %d (期望: 4)' % len(folders))

issues = []
stats = []

for folder in folders:
    fpath = os.path.join(mappings_dir, folder)
    if not os.path.isdir(fpath):
        continue
    files = [f for f in os.listdir(fpath) if not f.startswith('~') and not f.startswith('.')]
    
    print('\n[%s]' % folder)
    
    if len(files) == 0:
        print('  ❌ 无文件')
        issues.append('%s: 无文件' % folder)
        continue
    elif len(files) > 1:
        print('  ⚠️ 多个文件: %s' % files)
        issues.append('%s: 多个文件' % folder)
    
    fname = files[0]
    fsize = os.path.getsize(os.path.join(fpath, fname)) / 1024
    print('  文件: %s (%.1f KB)' % (fname, fsize))
    
    try:
        data = json.load(open(os.path.join(fpath, fname), encoding='utf-8'))
        print('  JSON格式: ✅ 有效')
        
        if '_说明' in data:
            print('  说明: %s' % str(data['_说明'])[:60])
        else:
            print('  ⚠️ 缺少 _说明 字段')
            issues.append('%s: 缺少_说明' % folder)
        
        if folder == '部门事业部映射':
            im = data.get('income_mapping', {})
            pm = data.get('payment_mapping', {})
            ic = len([k for k in im if not k.startswith('_')])
            pc = 0
            for k, v in pm.items():
                if isinstance(v, dict) and not k.startswith('_'):
                    pc += len([x for x in v if not str(x).startswith('_')])
            print('  收入映射: %d 条' % ic)
            print('  回款映射: %d 条' % pc)
            for dept in ['检测','信息','能源','海外']:
                if dept not in pm:
                    print('  ⚠️ 回款映射缺少事业部: %s' % dept)
                    issues.append('部门事业部映射: 缺少%s' % dept)
            excl = data.get('excluded_internal_companies', {}).get('companies', [])
            print('  内部交易排除: %d 家' % len(excl))
            # 验证映射值是否合法
            valid_depts = {'检测','信息','能源','海外'}
            for k, v in im.items():
                if not k.startswith('_') and v not in valid_depts:
                    print('  ⚠️ 收入映射值异常: %s -> %s' % (k, v))
                    issues.append('部门事业部映射: 收入映射值异常 %s' % k)
            stats.append(('部门事业部映射', '收入%d+回款%d+排除%d家' % (ic, pc, len(excl))))
            
        elif folder == '客户名单':
            customers = data.get('customers', [])
            print('  客户数: %d' % len(customers))
            if len(customers) == 0:
                issues.append('客户名单: 空列表')
            # 检查重复
            dup = len(customers) - len(set(customers))
            if dup > 0:
                print('  ⚠️ 重复客户: %d 个' % dup)
                issues.append('客户名单: %d个重复' % dup)
            else:
                print('  重复检查: ✅ 无重复')
            stats.append(('客户名单', '%d个客户' % len(customers)))
            
        elif folder == '客户统称名单':
            cm = data.get('company_mapping', {})
            total = sum(len(v) for v in cm.values())
            print('  母公司: %d 个' % len(cm))
            print('  子公司映射: %d 条' % total)
            # 检查子公司是否有重复
            all_subs = []
            for v in cm.values():
                all_subs.extend(v)
            dup = len(all_subs) - len(set(all_subs))
            if dup > 0:
                print('  ⚠️ 重复子公司: %d 个' % dup)
                issues.append('客户统称名单: %d个重复子公司' % dup)
            else:
                print('  重复检查: ✅ 无重复')
            stats.append(('客户统称名单', '%d母公司+%d子公司' % (len(cm), total)))
            
        elif folder == '客户销售对应规则':
            gd = data.get('广东公司规则', {})
            sz = data.get('深圳公司规则', {})
            qt = data.get('其他规则', {})
            df = data.get('默认规则', {})
            total_rule = len(gd) + len(sz) + len(qt) + len(df)
            print('  广东公司规则: %d' % len(gd))
            print('  深圳公司规则: %d' % len(sz))
            print('  其他规则: %d' % len(qt))
            print('  默认规则: %d' % len(df))
            print('  总规则数: %d' % total_rule)
            stat = data.get('_统计', {})
            if stat:
                print('  覆盖率: %s' % stat.get('总覆盖率', '未知'))
            # 检查是否有模糊匹配配置
            if '_模糊匹配' in data:
                print('  模糊匹配: ✅ 已配置')
            else:
                print('  ⚠️ 缺少模糊匹配配置')
                issues.append('客户销售对应规则: 缺少模糊匹配')
            stats.append(('客户销售对应规则', '广东%d+深圳%d+其他%d+默认%d=%d' % (
                len(gd), len(sz), len(qt), len(df), total_rule)))
            
    except json.JSONDecodeError as e:
        print('  JSON格式: ❌ 无效 - %s' % e)
        issues.append('%s: JSON格式错误' % folder)
    except Exception as e:
        print('  ❌ 读取失败: %s' % e)
        issues.append('%s: %s' % (folder, str(e)))

print('\n' + '=' * 60)
print('健康度总结')
print('=' * 60)
print('文件夹: %d/4' % len(folders))
print('问题数: %d' % len(issues))
if issues:
    print('\n问题列表:')
    for i in issues:
        print('  ❌ %s' % i)
else:
    print('\n✅ 全部通过，无问题')
print('\n统计:')
for name, desc in stats:
    print('  %s: %s' % (name, desc))
