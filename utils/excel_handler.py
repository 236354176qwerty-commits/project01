"""
Excel处理工具类
用于生成随行人员登记模板和解析上传的Excel文件
"""

import pandas as pd
from io import BytesIO
import re
from datetime import datetime

class ExcelHandler:
    def __init__(self):
        self.position_options = {
            '教练': 'head_coach',
            '领队': 'manager', 
            '医务人员': 'doctor',
            '其他': 'other'
        }
        
    def generate_staff_template(self):
        """
        生成随行人员登记Excel模板
        """
        # 创建模板数据
        template_data = {
            '姓名': ['张教练', '李领队', '王医生'],
            '职务': ['教练', '领队', '医务人员'],
            '联系电话': ['13800138001', '13900139002', '13700137003'],
            '身份证号': ['110101199001011234', '220202199002022345', '330303199003033456'],
            '证书/资质': ['国家级武术教练证', '体育管理证书', '执业医师证']
        }
        
        # 创建DataFrame
        df = pd.DataFrame(template_data)
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 写入数据到工作表
            df.to_excel(writer, sheet_name='随行人员信息', index=False)
            
            # 获取工作表对象
            worksheet = writer.sheets['随行人员信息']
            
            # 设置列宽
            column_widths = {
                'A': 15,  # 姓名
                'B': 12,  # 职务
                'C': 18,  # 联系电话
                'D': 20,  # 身份证号
                'E': 25   # 证书/资质
            }
            
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
            
            # 添加说明工作表
            instructions = pd.DataFrame({
                '填写说明': [
                    '1. 请按照模板格式填写随行人员信息',
                    '2. 姓名：请填写真实姓名，2-10个字符',
                    '3. 职务：只能选择"教练"、"领队"、"医务人员"、"其他"',
                    '4. 联系电话：请填写11位手机号码',
                    '5. 身份证号：请填写18位身份证号码',
                    '6. 证书/资质：相关职业证书或资质证明',
                    '7. 示例数据仅供参考，请删除后填写实际信息',
                    '8. 填写完成后保存并上传Excel文件'
                ]
            })
            
            instructions.to_excel(writer, sheet_name='填写说明', index=False)
            
            # 设置说明工作表列宽
            writer.sheets['填写说明'].column_dimensions['A'].width = 50
        
        output.seek(0)
        return output.getvalue()
    
    def parse_staff_excel(self, file_content):
        """
        解析上传的随行人员Excel文件
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(BytesIO(file_content), sheet_name='随行人员信息')
            
            # 验证必需的列
            required_columns = ['姓名', '职务', '联系电话', '身份证号', '证书/资质']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    'success': False,
                    'error': f'缺少必需的列: {", ".join(missing_columns)}'
                }
            
            # 处理数据
            staff_list = []
            errors = []
            
            for index, row in df.iterrows():
                row_num = index + 2  # Excel行号（从2开始，因为有标题行）
                
                # 验证数据
                validation_result = self._validate_staff_row(row, row_num)
                
                if validation_result['valid']:
                    staff_data = {
                        'name': str(row['姓名']).strip(),
                        'position': self.position_options.get(str(row['职务']).strip()),
                        'phone': str(row['联系电话']).strip(),
                        'idCard': str(row['身份证号']).strip(),
                        'certificate': str(row['证书/资质']).strip() if pd.notna(row['证书/资质']) else '',
                        'status': 'active'
                    }
                    staff_list.append(staff_data)
                else:
                    errors.extend(validation_result['errors'])
            
            if errors:
                return {
                    'success': False,
                    'error': '数据验证失败',
                    'details': errors
                }
            
            return {
                'success': True,
                'data': staff_list,
                'count': len(staff_list)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'文件解析失败: {str(e)}'
            }
    
    def _validate_staff_row(self, row, row_num):
        """
        验证单行数据
        """
        errors = []
        
        # 检查姓名
        name = str(row['姓名']).strip() if pd.notna(row['姓名']) else ''
        if not name:
            errors.append(f'第{row_num}行：姓名不能为空')
        elif len(name) < 2 or len(name) > 10:
            errors.append(f'第{row_num}行：姓名长度应为2-10个字符')
        
        # 检查职务
        position = str(row['职务']).strip() if pd.notna(row['职务']) else ''
        if not position:
            errors.append(f'第{row_num}行：职务不能为空')
        elif position not in self.position_options:
            errors.append(f'第{row_num}行：职务只能选择"教练"、"领队"、"医务人员"、"其他"')
        
        # 检查联系电话
        phone = str(row['联系电话']).strip() if pd.notna(row['联系电话']) else ''
        if not phone:
            errors.append(f'第{row_num}行：联系电话不能为空')
        elif not re.match(r'^1[3-9]\d{9}$', phone):
            errors.append(f'第{row_num}行：联系电话格式不正确（应为11位手机号）')
        
        # 检查身份证号
        id_card = str(row['身份证号']).strip() if pd.notna(row['身份证号']) else ''
        if not id_card:
            errors.append(f'第{row_num}行：身份证号不能为空')
        elif not re.match(r'^\d{17}[\dXx]$', id_card):
            errors.append(f'第{row_num}行：身份证号格式不正确（应为18位）')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def export_staff_data(self, staff_list):
        """
        导出现有随行人员数据为Excel
        """
        if not staff_list:
            return None
        
        # 转换数据格式
        export_data = []
        position_map = {v: k for k, v in self.position_options.items()}
        
        for staff in staff_list:
            export_data.append({
                '姓名': staff.get('name', ''),
                '职务': position_map.get(staff.get('position', ''), '其他'),
                '联系电话': staff.get('phone', ''),
                '身份证号': staff.get('idCard', ''),
                '证书/资质': staff.get('certificate', ''),
                '状态': '正常' if staff.get('status') == 'active' else '停用'
            })
        
        # 创建DataFrame
        df = pd.DataFrame(export_data)
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='随行人员信息', index=False)
            
            # 设置列宽
            worksheet = writer.sheets['随行人员信息']
            column_widths = {
                'A': 15, 'B': 12, 'C': 18, 'D': 20, 'E': 25, 'F': 10
            }
            
            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width
        
        output.seek(0)
        return output.getvalue()
