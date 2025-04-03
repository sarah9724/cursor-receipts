import json

class Database:
    def get_free_uses(self, phone):
        """获取用户的剩余免费次数"""
        collection = self.client.get_collection(self.USER_COLLECTION)
        result = collection.get(f"phone:{phone}")
        if result:
            user_data = json.loads(result)
            return user_data.get('free_uses', 0)
        return 0

    def use_free_chance(self, phone):
        """使用一次免费机会
        
        返回：
            bool: 如果成功使用返回True，如果没有剩余次数返回False
        """
        collection = self.client.get_collection(self.USER_COLLECTION)
        result = collection.get(f"phone:{phone}")
        
        if not result:
            return False
        
        user_data = json.loads(result)
        free_uses = user_data.get('free_uses', 0)
        
        if free_uses > 0:
            user_data['free_uses'] = free_uses - 1
            collection.put(f"phone:{phone}", json.dumps(user_data))
            return True
        
        return False 