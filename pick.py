import sys
import csv
import random
import os
from collections import defaultdict

DATA_FILE = 'cards.csv'
BAN_FILE = 'ban_status.csv'

class CardManager:
    def __init__(self):
        self.cards = []  # [{'name': str, 'weight': float, 'tags': set}]
        self.ban_status = defaultdict(bool)  # {tag: bool}
        self._load_data()
        self._load_ban_status()
    
    def _load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 2:
                        continue
                    name = row[0]
                    weight = float(row[1])
                    tags = set(row[2:]) if len(row) > 2 else set()
                    self.cards.append({'name': name, 'weight': weight, 'tags': tags})
    
    def _load_ban_status(self):
        if os.path.exists(BAN_FILE):
            with open(BAN_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        tag, status = row[0], row[1]
                        self.ban_status[tag] = (status == '1')
    
    def _save_data(self):
        with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for card in self.cards:
                row = [card['name'], str(card['weight'])] + list(card['tags'])
                writer.writerow(row)
    
    def _save_ban_status(self):
        with open(BAN_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for tag, banned in self.ban_status.items():
                writer.writerow([tag, '1' if banned else '0'])
    
    def _get_total_weight(self, include_banned=False):
        if include_banned:
            return sum(card['weight'] for card in self.cards)
        
        total = 0.0
        for card in self.cards:
            if not self._is_card_banned(card):
                total += card['weight']
        return total
    
    def _is_card_banned(self, card):
        for tag in card['tags']:
            if self.ban_status.get(tag, False):
                return True
        return False
    
    def _find_card(self, name):
        for i, card in enumerate(self.cards):
            if card['name'] == name:
                return i, card
        return -1, None
    
    def add_card(self, name, weight):
        weight = max(0.0, float(weight))
        idx, card = self._find_card(name)
        
        if idx >= 0:
            card['weight'] = weight
        else:
            self.cards.append({'name': name, 'weight': weight, 'tags': set()})
        
        self._save_data()
        return self._get_normalized_probability(name)
    
    def _get_normalized_probability(self, name):
        total = self._get_total_weight(include_banned=False)
        _, card = self._find_card(name)
        
        if card is None or self._is_card_banned(card):
            return 0.0
        
        if total == 0:
            return 0.0
            
        return (card['weight'] / total) * 100
    
    def list_cards(self):
        total_valid = self._get_total_weight(include_banned=False)
        
        valid_cards = []
        banned_cards = []
        
        for card in self.cards:
            banned = self._is_card_banned(card)
            tags = ', '.join(sorted(card['tags'])) if card['tags'] else '无'
            
            if banned:
                prob = 0.0
                banned_cards.append({
                    'name': card['name'] + " [BANNED]",
                    'weight': card['weight'],
                    'probability': prob,
                    'tags': tags
                })
            else:
                prob = (card['weight'] / total_valid * 100) if total_valid > 0 else 0.0
                valid_cards.append({
                    'name': card['name'],
                    'weight': card['weight'],
                    'probability': prob,
                    'tags': tags
                })
        
        valid_cards.sort(key=lambda x: x['probability'], reverse=True)
        banned_cards.sort(key=lambda x: x['weight'], reverse=True)
        
        return valid_cards + banned_cards
    
    def tag_card(self, name, tag):
        idx, card = self._find_card(name)
        if idx < 0:
            return False
        card['tags'].add(tag)
        self._save_data()
        return True
    
    def set_normalized_probability(self, name, target_prob):
        target_prob = float(target_prob)
        idx, card = self._find_card(name)
        if idx < 0:
            return False
        
        if target_prob == 0:
            del self.cards[idx]
            self._save_data()
            return True
        
        total = self._get_total_weight(include_banned=True)
        others_weight = total - card['weight']
        
        if others_weight == 0:
            card['weight'] = 1.0
        else:
            new_weight = (target_prob * others_weight) / (100.0 - target_prob)
            card['weight'] = max(0.0, new_weight)
        
        self._save_data()
        return True
    
    def adjust_tag_probability(self, tag, target_prob):
        target_prob = float(target_prob)
        tag_cards = [card for card in self.cards if tag in card['tags']]
        other_cards = [card for card in self.cards if tag not in card['tags']]
        
        if not tag_cards:
            return False
        
        tag_weight = sum(card['weight'] for card in tag_cards)
        other_weight = sum(card['weight'] for card in other_cards)
        
        if target_prob == 0:
            for card in tag_cards:
                card['weight'] = 0.0
        elif target_prob == 100:
            if other_weight > 0:
                return False
        else:
            if tag_weight == 0:
                return False
            k = (target_prob * other_weight) / (tag_weight * (100.0 - target_prob))
            for card in tag_cards:
                card['weight'] *= k
        
        self._save_data()
        return True
    
    def pick_card(self, count=1):
        valid_cards = []
        weights = []
        for card in self.cards:
            if not self._is_card_banned(card):
                valid_cards.append(card)
                weights.append(card['weight'])
        
        total = sum(weights)
        if total <= 0:
            return None
        
        # 确保每次抽取都是独立的
        results = []
        for _ in range(count):
            chosen = random.choices(valid_cards, weights=weights, k=1)[0]
            results.append(chosen['name'])
        
        if count == 1:
            return results[0]
        else:
            return results
    
    def delete_card(self, name):
        """删除指定卡牌"""
        idx, card = self._find_card(name)
        if idx < 0:
            return False
        
        del self.cards[idx]
        self._save_data()
        return True
    
    def test_randomness(self, card_name, trials=10000):
        """测试特定卡牌的出现频率"""
        count = 0
        for _ in range(trials):
            result = self.pick_card()
            if result == card_name:
                count += 1
        
        probability = count / trials * 100
        expected = self._get_normalized_probability(card_name)
        
        print(f"测试结果: {card_name}")
        print(f"预期概率: {expected:.4f}%")
        print(f"实际频率: {probability:.4f}%")
        print(f"差异: {abs(expected - probability):.4f}%")
    
    def ban_tag(self, tag, status):
        status = status.strip()
        if status not in ['0', '1']:
            return False
        
        banned = (status == '1')
        self.ban_status[tag] = banned
        self._save_ban_status()
        return True

def main():
    if len(sys.argv) < 2:
        print("请使用以下命令:")
        print("  -p, --pick [次数]: 随机抽取一张或多张卡 (默认1次)")
        print("  -a, --add [名称|权重]: 添加/更新卡牌")
        print("  -d, --delete [名称]: 删除卡牌")
        print("  -l, --list: 列出所有卡牌")
        print("  -t, --tag [卡名|标签]: 给卡牌添加标签")
        print("  -s, --set [卡名|概率]: 设置卡牌归一化概率")
        print("  --tag-adjust [标签|概率]: 调整标签整体概率")
        print("  --ban-tag [标签|状态]: 屏蔽标签 (1=屏蔽, 0=不屏蔽)")
        print("  --test [卡名|测试次数]: 测试卡牌出现频率")
        return
    
    manager = CardManager()
    command = sys.argv[1]
    
    try:
        if command in ['-p', '--pick']:
            count = 1
            
            if len(sys.argv) >= 3:
                try:
                    count = int(sys.argv[2])
                    if count < 1:
                        print("错误: 抽取次数必须大于0")
                        return
                except ValueError:
                    print("错误: 无效的抽取次数")
                    return
            
            if count == 1:
                card = manager.pick_card(count)
                print(f"抽到了: {card}" if card else "卡池为空!")
            else:
                results = manager.pick_card(count)
                if not results:
                    print("卡池为空!")
                    return
                
                print(f"抽取 {count} 次结果:")
                for i, card in enumerate(results, 1):
                    print(f"{i}. {card}")
        
        elif command in ['-a', '--add']:
            if len(sys.argv) < 3:
                print("缺少参数，格式: --add 名称|权重")
                return
            name, weight = sys.argv[2].split('|', 1)
            prob = manager.add_card(name, weight)
            print(f"卡牌 '{name}' 添加成功! 当前概率: {prob:.2f}%")
        
        elif command in ['-d', '--delete']:
            if len(sys.argv) < 3:
                print("缺少参数，格式: --delete 名称")
                return
            name = sys.argv[2]
            if manager.delete_card(name):
                print(f"卡牌 '{name}' 已成功删除")
            else:
                print(f"错误: 卡牌 '{name}' 不存在")
        
        elif command in ['-l', '--list']:
            cards = manager.list_cards()
            if not cards:
                print("卡池为空")
                return
            
            print(f"{'名称':<25} {'权重':<10} {'概率(%)':<10} {'标签':<20}")
            print("-" * 70)
            
            for card in cards:
                print(f"{card['name']:<25} {card['weight']:<10.2f} {card['probability']:<10.2f} {card['tags']}")
        
        elif command in ['-t', '--tag']:
            if len(sys.argv) < 3:
                print("缺少参数，格式: --tag 卡名|标签")
                return
            name, tag = sys.argv[2].split('|', 1)
            if manager.tag_card(name, tag):
                print(f"已为 '{name}' 添加标签 '{tag}'")
            else:
                print(f"错误: 卡牌 '{name}' 不存在")
        
        elif command in ['-s', '--set']:
            if len(sys.argv) < 3:
                print("缺少参数，格式: --set 卡名|概率")
                return
            name, prob = sys.argv[2].split('|', 1)
            if manager.set_normalized_probability(name, prob):
                print(f"已更新 '{name}' 的概率")
            else:
                print(f"错误: 卡牌 '{name}' 不存在")
        
        elif command == '--tag-adjust':
            if len(sys.argv) < 3:
                print("缺少参数，格式: --tag-adjust 标签|概率")
                return
            tag, prob = sys.argv[2].split('|', 1)
            if manager.adjust_tag_probability(tag, prob):
                print(f"标签 '{tag}' 的概率已调整为 {prob}%")
            else:
                print(f"错误: 调整失败 (标签不存在或无效参数)")
        
        elif command == '--ban-tag':
            if len(sys.argv) < 3:
                print("缺少参数，格式: --ban-tag 标签|状态")
                return
            tag, status = sys.argv[2].split('|', 1)
            if manager.ban_tag(tag, status):
                action = "屏蔽" if status == '1' else "取消屏蔽"
                print(f"已{action}标签 '{tag}'")
            else:
                print(f"错误: 无效的状态值 '{status}' (应为0或1)")
        
        elif command == '--test':
            if len(sys.argv) < 3:
                print("格式: --test 卡名|测试次数")
                return
            card_name, trials = sys.argv[2].split('|', 1)
            manager.test_randomness(card_name, int(trials))
        
        else:
            print("未知命令")
    
    except Exception as e:
        print(f"操作失败: {str(e)}")

if __name__ == '__main__':
    main()