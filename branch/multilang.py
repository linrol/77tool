import pandas as pd
import os
import csv
import requests
import json
import time
import sys
import traceback


class LangTranslater:
    def run(self, text):
        return self.translate_use_77hub(text, "vocabulary", 0)

    def translate_use_77hub(self, text, source, retry):
        if retry > 3:
            return False, ""
        url = "http://52.83.252.105:3000/api/v1/chat/completions"
        key = ("fastgpt-JQfCEvQpN0j8jTkXB3ulh3pGtp67ulHEnVKaEmGd8gZZW0lnLC0JYja" if source == "vocabulary" else "fastgpt-scYdy1EwipUsSkAQZTpqr50UnDzfxC5BQdFNKcAsNzzCgEetoYjU")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        params = {
            "stream": False,
            "detail": False,
            "chatId": "",
            "variables": {
                "textType": "data",
                "translateFormat": "JSON"
            },
            "messages": [{"content": text, "role": "user"}]
        }
        request_body = json.dumps(params)
        try:
            response = requests.post(url, headers=headers, data=request_body, timeout=20)
            response_data = response.json()
            choices = response_data.get("choices", [])
            for choice in choices:
                role = choice.get("message", {}).get("role")
                if role == "assistant":
                    content = choice.get("message", {}).get("content")
                    if content:
                        if source == "vocabulary":
                            parsed_content = json.loads(content)
                            for item in parsed_content:
                                if item.get("q") == text:
                                    translation = item.get("a", "")
                                    print(f"使用企企翻译助手翻译【{text}】:【{translation}】")
                                    return True, translation
                        else:
                            parsed_content = json.loads(content.replace("```", "").replace("json", ""))
                            translation = parsed_content.get("english", "")
                            print(f"使用企企翻译助手翻译【{text}】:【{translation}】")
                            return True, translation
            if source == "vocabulary":
                return self.translate_use_77hub(text, "translate", retry + 1)
            else:
                print(f"使用企企翻译助手翻译【{text}】:出现错误【{response.text}】")
                return False, ""
        except Exception as e:
            traceback.print_exc()
            print(e)
            time.sleep(5)  # 暂停5秒继续翻译
            return self.translate_use_77hub(text, source, retry + 1)


class MultiLangFile:
    def __init__(self, _chinese_index, _english_index):
        self.chinese_index = int(_chinese_index)
        self.english_index = int(_english_index)
        self.max_retry = 3
        self.translater = LangTranslater()

    def translate(self, file_path, retry_num, cnt):
        if retry_num > self.max_retry:
            return
        df = pd.read_csv(file_path)  # 读取CSV文件
        done = True
        for index, row in df.iterrows():
            chinese = row.iloc[self.chinese_index]
            english = row.iloc[self.english_index]
            blank_chinese = pd.isna(chinese) or self.is_empty(chinese)
            blank_english = pd.isna(english) or self.is_empty(english)
            if blank_chinese or (not blank_english):
                continue  # 中文列为空或者英文列不为空，则不需要翻译
            row_ret, df.iloc[index, self.english_index] = self.translater.run(chinese)
            cnt += (1 if row_ret else 0)
            done = row_ret and done
        if cnt > 0:
            df.to_csv(file_path, index=False, quoting=csv.QUOTE_ALL)
        return cnt if done else self.translate(file_path, retry_num + 1, 0)

    @staticmethod
    def is_csv_file(file_path):
        if not os.path.isfile(file_path):
            return False
        return os.path.splitext(file_path)[1].lower() == '.csv'

    @staticmethod
    def is_empty(var):
        if not isinstance(var, str):
            return False
        return len(var) == 0

    def run(self, _path):
        for entry in os.listdir(_path):
            child_path = os.path.join(_path, entry)
            if os.path.isdir(child_path):
                self.run(child_path)
            elif self.is_csv_file(child_path):
                print(f"文件 {child_path} 开始翻译...")
                try:
                    cnt = self.translate(child_path, 1, 0)
                    print(f"文件 {child_path} 总共翻译了 {cnt} 条")
                except Exception as e:
                    traceback.print_exc()
                    print(f"文件 {child_path} 翻译失败 {e}")
            else:
                print(f"文件 {child_path} 忽略")


# 翻译目录下csv文件的中文列内容到英文列
# python3 multilang.py src/main/resources/multi-langs 2 1
# 参数说明：<目录:src/main/resources/multi-langs> <中文列:2> <英文列:1>
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: 输入参数错误, 正确的参数为：<path> <chinese column index> <english column index>")
        sys.exit(1)
    else:
        path = sys.argv[1]
        chinese_index = sys.argv[2]
        english_index = sys.argv[3]
        MultiLangFile(chinese_index, english_index).run(path)





