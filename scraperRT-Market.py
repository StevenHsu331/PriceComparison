import bs4
import urllib.request as lib
import string
import math
import pymysql
import re

# 避免將資料庫資訊暴露在程式碼中, 另外儲存在讀取
def get_db_settings():
    with open("dbsetting.txt") as setting:
        db_settings = {}
        result = setting.read()
        result = result.replace("\n", "")
        result = result.split(",")

        for i in range(len(result)):
            result[i] = result[i].split(":")
            if i == 1:
                db_settings[result[i][0]] = int(result[i][1])
            else:
                db_settings[result[i][0]] = result[i][1]

        return db_settings


# 爬蟲程式
def getHomeData(url, product_info):
    

    # 取得產品規格ex 幾ml, 幾抽幾包....
    def getProductDetail(url):
        request = lib.Request(url,headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"
        })

        with lib.urlopen(request) as response:
            data = response.read().decode("utf-8")

        root = bs4.BeautifulSoup(data, "html.parser")
        table = root.find("table", class_="title_word")
        sub_table = table.find("table", attrs={"cellspacing":"0","cellpadding": "0","width": "100%","border":"0"})
        target = sub_table.find("td").text.strip().split("\n")
        print(target[0].split(":", 1)[1])
        return target[0].split(":", 1)[1]


    # 獲取目標頁中所有商品的名稱, 價格及規格
    def getPageData(url, product_info, category):
        request = lib.Request(url,headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"
        })

        with lib.urlopen(request) as response:
            data = response.read().decode("utf-8")

        root = bs4.BeautifulSoup(data, "html.parser")
        next_tag = root.find("li", class_ = "next")  # 取得下一頁的按鈕

        # 若找得到下一頁的按鈕即代表還有下一頁
        if next_tag:
            return_val = next_tag.find("a", href=True)['href']
            products = root.find_all("div", class_ = "indexProList")

            for product in products:
                name_tag = product.findChild("h5", class_="for_proname")
                price_tag = product.findChild("div", class_="for_pricebox")
                prices = price_tag.findChildren("span")
                result = 0

                # 缺貨時price會顯示"售完，補貨中", 故無法轉成int
                try:
                    result = int(prices[-1].text[1:]) if prices[-1].text[0] == "$" else int(prices.text[-1])
                except:
                    result = prices[-1].text
                
                print(name_tag.findChild("a").text, result)
                product_info[category].append([name_tag.findChild("a").text, result, getProductDetail(name_tag.findChild("a")["href"])])

            if return_val[:33] != "https://www.rt-mart.com.tw/direct/":
                return_val = "https://www.rt-mart.com.tw/direct/" + return_val

            return return_val
        else:
            left_boxes = root.find_all("div", class_ = "classify_leftBox")

            for left_box in left_boxes:
                a_tag = left_box.find("h3", class_="classify_title")
                getPageData(a_tag.find("a", href=True)['href'], product_info, category)


    # 獲取小分類中每一頁的商品
    def getCategoryData(url, product_info, category):
        request = lib.Request(url, headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"
        })

        with lib.urlopen(request) as response:
            data = response.read().decode("utf-8")

        root = bs4.BeautifulSoup(data,"html.parser")
        next_tag = root.find("li", class_ = "next")
        page_num = math.ceil(int(root.find("span", class_="t02").text) / 18)

        for i in range(page_num):
            if i == 0:
                next_tag = getPageData(url, product_info, category)
            else:
                # 每一次新的next_tag需要用舊的next_tag去抓, 故用兩個變數交互assign
                if i % 2 == 1:
                    next_tag2 =  getPageData(next_tag, product_info, category)
                else:
                    next_tag = getPageData(next_tag2, product_info, category)


    # 獲取導覽列上所有大分類
    def getNavData(url, product_info, category):
        request = lib.Request(url, headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"
        })

        with lib.urlopen(request) as response:
            data = response.read().decode("utf-8")

        root = bs4.BeautifulSoup(data, "html.parser")
        left_boxes = root.find_all("div", class_ = "classify_leftBox")

        # 找到導覽列中所有子分類
        for left_box in left_boxes:
            a_tag = left_box.find("h3", class_="classify_title")

            # 當href = "javascript: void(0);"代表目前頁面即為該分類的商品, 不需要再抓取href
            # 接著去抓取該子分類中每一頁的商品
            if a_tag.find("a", href=True)['href'] == "javascript: void(0);":
                getCategoryData(url, product_info, category)
            else:
                getCategoryData(a_tag.find("a", href=True)['href'], product_info, category)

    request = lib.Request(url,headers={
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36"
    })

    with lib.urlopen(request) as response:
        data = response.read().decode("utf-8")

    root = bs4.BeautifulSoup(data, "html.parser")
    navs = root.find_all("li", class_="nav01")
    navs += root.find_all("li", class_="nav02")

    for nav in navs:
        a = nav.findChild("a", href=True)

        # 該網頁導覽列有一個空的a tag, 需忽略
        if a == None:
            continue
        
        print(a.text)
        target_href = a['href']
        product_info[a.text] = []  # 初始化dict中該分類的value為空list
        
        if target_href[:34] != "https://www.rt-mart.com.tw/direct/" and target_href[:33] != "http://www.rt-mart.com.tw/direct/":
            target_href = "https://www.rt-mart.com.tw/direct/" + target_href
            getNavData(target_href, product_info, a.text)
        else:
            getNavData(target_href, product_info, a.text)


# 刪除字串中所有空格
def trim(string):
    return string.replace(" ", "")


# 將資料存入資料庫
def insert_into_db(data):
    db_settings = get_db_settings()

    con = pymysql.connect(**db_settings)

    with con.cursor() as cursor:
        delCom = "delete from products_info where market = 'RT-Market'"  # 先將原本的資料全數刪除再輸入新的資料
        com = "insert into products_info (product_name, product_price, category, market, cp_val, status, detail) values(%s, %s, %s, %s, %s, %s, %s)"

        # cursor.execute(delCom)
        # con.commit()

        for product_data in data.items():
            print(product_data[0])

            for info in product_data[1]:
                info[0] = strQtoB(info[0]).strip()  # 先統一轉成半形
                print(info[0], info[1], info[2], sep=",")

                # # 若價格非數字代表是 "售完，補貨中", 所以必須將status設為0, price 設為 -1
                # if type(info[1]) is int:
                #     cursor.execute(com, (trim(info[0]), info[1], trim(product_data[0]), "RT-Market", 0, 1, trim(info[2])))
                # else:
                #     cursor.execute(com, (trim(info[0]), 0, trim(product_data[0]), "RT-Market", 0, 0, trim(info[2])))
                # con.commit()

    con.close()


# 算出所有商品的CP值
def count_all_cp():

    # 下面先從資料庫中取出所有大潤發的商品資料
    db_settings = get_db_settings()

    con = pymysql.connect(**db_settings)
    skip_categories = ["3C電子/配件", "大型家電/視聽影音", "傢俱寢飾", "小家電專區", "戶外休閒"]

    with con.cursor() as cursor:
        select = "select * from products_info where market = 'RT-Market'"
        update = "update products_info set cp_val = %s, cp_val_unit = %s where market = 'RT-Market' and product_name = %s and detail = %s and product_price = %s"
        update_without_unit = "update products_info set cp_val = %s, cp_val_unit = %s where market = 'RT-Market' and product_name = %s and detail = %s and product_price = %s"

        cursor.execute(select)
        result = cursor.fetchall()
        
        for info in result:
            if info[2].strip() not in skip_categories:
                cp_val = countCP(list(info))

                # if len(cp_val) == 1:
                #     cursor.execute(
                #         update_without_unit,
                #         (cp_val[0], "", info[0], info[6], info[1])
                #     )
                #     con.commit()
                # else:
                #     cursor.execute(
                #         update,
                #         (cp_val[1], cp_val[0], info[0], info[6], info[1])
                #     )
                #     con.commit()

        print(len(result))


# 大潤發網站中全形半形並未統一
def strQtoB(s):
    """把字串全形轉半形"""
    rstring = ""
    for uchar in s:
        u_code = ord(uchar)
        if u_code == 12288:  # 全形空格直接轉換
            u_code = 32
        elif 65281 <= u_code <= 65374:  # 全形字元（除空格）根據關係轉化
            u_code -= 65248
        rstring += chr(u_code)
    return rstring


def findKeywords(target):

    # 先看有沒有乘的符號且符號後面接的是數字, 有就分割字串(需判斷有無數字否則會出錯 ex. XO醬)
    if re.search(r"\*+\d+", target[0]):
        target[0] = target[0].split("*")
    elif re.search(r"x+\d+", target[0]):
        target[0] = target[0].split("x")
    elif re.search(r"X+\d+", target[0]):
        target[0] = target[0].split("X")
    else:
        # 最後無論如何都把target[0]轉成list, 因為下面都是將target[0]作為list做操作
        target[0] = [target[0]]

    status = False  # 代表該商品是否有詳細的規格(代表是否可以計算出cp值)

    # 要查找的單位量詞
    unit_condition = r"(罐|盒|抽|包|瓶|袋|入|錠|粒|杯|塊|顆|片|條|尾|件|雙|組|台|本|卡|支|個|碗|桶|捲|KG|kg|G|g|L|ML|ml|c\.c|cc|oz|公斤|克|公克|公升|毫升)"  # 後續正則式需用到的單位關鍵字

    result = [0]
    search_target_val = target[0][0]  # 等等尋找單位量詞的目標字串

    # 利用正則式找尋是否有 浮點數或整數 + 單位量詞在字串內
    number = re.search(
        r"(\+*\d+\.+\d+{}+)|(\+*\d+{}+)".format(unit_condition, unit_condition),
            search_target_val
        )

    # 若有找到數字+量詞則將字串進行分割並反覆尋找直到找不到為止
    # 利用result儲存找到的結果
    while number:

        status = True
        result.pop(-1)
        number = number.span()
        units = search_target_val[number[0]:number[1]]
        units_number = re.search(r"\+*\d+\.*\d*", units).span()

        result.extend([
            search_target_val[:number[0]],
            search_target_val[number[0]:number[0]+units_number[1]], 
            search_target_val[number[0]+units_number[1]:number[1]],
            search_target_val[number[1]:]
        ])

        search_target_val = search_target_val[number[1]:]  # 將要查找的字串更新為找到的量詞後的字串(再往後找有沒有量詞)

        number = re.search(
            r"(\+*\d+\.+\d+{}+)|(\+*\d+{}+)".format(unit_condition, unit_condition),
            search_target_val
        )

    value = 0

    if status:
        value = 1
        
        for i in range(1, len(result) - 1):

            if result[i] == "+-":
                value /= float(result[i+1])
                continue

            if re.match(r"\+*[0-9]+\.*[0-9]*", result[i]):

                # 此為因應有些產品會有包含運算的數量ex:3+1包, 因此必須作特殊的處裡
                if re.match(r"\+", result[i]):
                    for j in range(i - 1, 0, -1):
                        if re.match(r"[0-9]+\.*[0-9]*", result[j]):
                            value /= float(result[j])
                            value *= float(result[i]) + float(result[j])
                            break
                else:
                    value *= float(result[i])
        
        # 除了分析result中的結果之外, 還需分析最一開始用乘法符號作分割的結果
        if len(target[0]) > 1:
            
            number = re.match(r"[0-9]+\.*[0-9]*({}+|\b)".format(unit_condition), target[0][1])
            number = number.span() if number != None else None

            if number:
                number = re.match(r"[0-9]+\.*[0-9]*", target[0][1]).span()
                value *= float(target[0][1][number[0]:number[1]])
                
        return (status, value, result[2])

    # 有時候雖然沒有找到相關的單位量詞, 但也需分析最一開始用乘法符號作分割的結果
    if len(target[0]) > 1:

        value = 1
        number = re.match(r"[0-9]+\.*[0-9]*{}+".format(unit_condition), target[0][1])
        number = number.span() if number != None else None

        if number:
            status = True # 若乘法符號後有相關單位就將status改為True
            number = re.match(r"[0-9]+\.*[0-9]*", target[0][1]).span()
            value *= float(target[0][1][number[0]:number[1]])
            return (status, value, target[0][1][number[1]:])

    return (status, value, 0)


# 根據規格算出商品cp值
def countCP(product):
    
    product[0] = trim(product[0])
    product[6] = trim(product[6])
    product_name = re.split(r"/+(罐|盒|抽|包|瓶|袋|入|錠|粒|杯|塊|顆|片|條|尾|件|雙|組|台|本|卡|支|個|碗|桶|捲|KG|kg|G|g|L|ML|ml|c\.c|cc|oz|公斤|克|公克|公升|毫升)+", product[0], 1)
    product_detail = re.split(r"/+(罐|盒|抽|包|瓶|袋|入|錠|粒|杯|塊|顆|片|條|尾|件|雙|組|台|本|卡|支|個|碗|桶|捲|KG|kg|G|g|L|ML|ml|c\.c|cc|oz|公斤|克|公克|公升|毫升)+", product[6], 1)
    
    result = [False, 0, 0]
    result_name = findKeywords(product_name)
    result_detail = findKeywords(product_detail)

    # 之所以要分別用name和detail去判斷cp值是因為有時候兩者給的規格不相同
    # 下面的判斷最終的result應採取name的還是detail的
    # 而判斷依據為: 先選擇有算出cp值的(及findKeywords return的第一個值為true)
    # 若兩個判斷出來都有cp值就選value大的(由於在這個階段只會算出商品有多少單位, 故越多單位代表資訊越詳細)
    # ex. 500ml*24罐(12000單位) vs. 24罐(24單位)
    if result_name[0] and result_detail[0]:
        result = result_detail if result_detail[1] > result_name[1] else result_name
    else:
        result = result_detail if result_detail[0] else result_name

    if not result[0] or product[1] == 0:
        print("NoCp:", product[1])
        return [product[1]]
    else:
        print("每{} {}元".format(result[2], format(float(product[1]) / result[1], ".2f")))
        return [result[2], format(float(product[1]) / result[1], ".2f")]


# product_data = {}
# url = "https://www.rt-mart.com.tw/direct/index.php?"
# getHomeData(url, product_data)
# insert_into_db(product_data)
count_all_cp()