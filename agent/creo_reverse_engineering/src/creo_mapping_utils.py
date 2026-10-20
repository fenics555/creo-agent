import os
import sys

# Добавляем пути для импортов
sys.path.append('D:/AI/tools/agent')
sys.path.append('D:/AI/tools/agent/creo_reverse_engineering/src')

def build_feat_body_map(features):
    """
    Создает словарь маппинга body_id -> feat_id.
    Это необходимо для связи геометрических объектов (GeomDepen) с их признаками (feat_id).
    
    :param features: Список словарей, возвращаемых scan_all_features.
    :return: dict {body_id: feat_id}
    """
    mapping = {}
    for feat in features:
        fid = feat.get('id')
        bid = feat.get('body_id')
        
        if fid and bid:
            # Если один body_id привязан к нескольму feat_id (бывает в сложных моделях), 
            # сохраняем список или берем последний. Для начала - последний.
            mapping[str(bid)] = str(fid)
            
    return mapping

def find_feat_by_body_id(mapping, body_id):
    """
    Находит feat_id по body_id.
    """
    if not body_id:
        return None
    return mapping.get(str(body_id))

if __name__ == "__main__":
    # Тестовый запуск
    test_features = [
        {'id': '100', 'body_id': '5000', 'params': []},
        {'id': '101', 'body_id': '5001', 'params': []},
        {'id': '102', 'body_id': '5000', 'params': []}, # Перезапишет 100
    ]
    
    mapping = build_feat_body_map(test_features)
    print(f"Mapping: {mapping}")
    print(f"Lookup 5000: {find_feat_by_body_id(mapping, '5000')}")
    print(f"Lookup 5001: {find_feat_by_body_id(mapping, '5001')}")
    print(f"Lookup 9999: {find_feat_by_body_id(mapping, '9999')}")
