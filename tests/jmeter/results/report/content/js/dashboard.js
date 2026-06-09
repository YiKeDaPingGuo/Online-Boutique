/*
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
var showControllersOnly = false;
var seriesFilter = "";
var filtersOnlySampleSeries = true;

/*
 * Add header in statistics table to group metrics by category
 * format
 *
 */
function summaryTableHeader(header) {
    var newRow = header.insertRow(-1);
    newRow.className = "tablesorter-no-sort";
    var cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Requests";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 3;
    cell.innerHTML = "Executions";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 7;
    cell.innerHTML = "Response Times (ms)";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Throughput";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 2;
    cell.innerHTML = "Network (KB/sec)";
    newRow.appendChild(cell);
}

/*
 * Populates the table identified by id parameter with the specified data and
 * format
 *
 */
function createTable(table, info, formatter, defaultSorts, seriesIndex, headerCreator) {
    var tableRef = table[0];

    // Create header and populate it with data.titles array
    var header = tableRef.createTHead();

    // Call callback is available
    if(headerCreator) {
        headerCreator(header);
    }

    var newRow = header.insertRow(-1);
    for (var index = 0; index < info.titles.length; index++) {
        var cell = document.createElement('th');
        cell.innerHTML = info.titles[index];
        newRow.appendChild(cell);
    }

    var tBody;

    // Create overall body if defined
    if(info.overall){
        tBody = document.createElement('tbody');
        tBody.className = "tablesorter-no-sort";
        tableRef.appendChild(tBody);
        var newRow = tBody.insertRow(-1);
        var data = info.overall.data;
        for(var index=0;index < data.length; index++){
            var cell = newRow.insertCell(-1);
            cell.innerHTML = formatter ? formatter(index, data[index]): data[index];
        }
    }

    // Create regular body
    tBody = document.createElement('tbody');
    tableRef.appendChild(tBody);

    var regexp;
    if(seriesFilter) {
        regexp = new RegExp(seriesFilter, 'i');
    }
    // Populate body with data.items array
    for(var index=0; index < info.items.length; index++){
        var item = info.items[index];
        if((!regexp || filtersOnlySampleSeries && !info.supportsControllersDiscrimination || regexp.test(item.data[seriesIndex]))
                &&
                (!showControllersOnly || !info.supportsControllersDiscrimination || item.isController)){
            if(item.data.length > 0) {
                var newRow = tBody.insertRow(-1);
                for(var col=0; col < item.data.length; col++){
                    var cell = newRow.insertCell(-1);
                    cell.innerHTML = formatter ? formatter(col, item.data[col]) : item.data[col];
                }
            }
        }
    }

    // Add support of columns sort
    table.tablesorter({sortList : defaultSorts});
}

$(document).ready(function() {

    // Customize table sorter default options
    $.extend( $.tablesorter.defaults, {
        theme: 'blue',
        cssInfoBlock: "tablesorter-no-sort",
        widthFixed: true,
        widgets: ['zebra']
    });

    var data = {"OkPercent": 97.44227353463587, "KoPercent": 2.5577264653641207};
    var dataset = [
        {
            "label" : "FAIL",
            "data" : data.KoPercent,
            "color" : "#FF6347"
        },
        {
            "label" : "PASS",
            "data" : data.OkPercent,
            "color" : "#9ACD32"
        }];
    $.plot($("#flot-requests-summary"), dataset, {
        series : {
            pie : {
                show : true,
                radius : 1,
                label : {
                    show : true,
                    radius : 3 / 4,
                    formatter : function(label, series) {
                        return '<div style="font-size:8pt;text-align:center;padding:2px;color:white;">'
                            + label
                            + '<br/>'
                            + Math.round10(series.percent, -2)
                            + '%</div>';
                    },
                    background : {
                        opacity : 0.5,
                        color : '#000'
                    }
                }
            }
        },
        legend : {
            show : true
        }
    });

    // Creates APDEX table
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.5060390763765542, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [0.625, 500, 1500, "2. 查看商品详情 GET /product/6E92ZMYYFZ"], "isController": false}, {"data": [0.4072727272727273, 500, 1500, "5. 清空购物车 POST /cart/empty-1"], "isController": false}, {"data": [0.5333333333333333, 500, 1500, "商品详情 GET /product/OLJCESPC7Z"], "isController": false}, {"data": [0.193, 500, 1500, "首页 GET /"], "isController": false}, {"data": [0.9854545454545455, 500, 1500, "5. 清空购物车 POST /cart/empty-0"], "isController": false}, {"data": [0.6086956521739131, 500, 1500, "2. 查看商品详情 GET /product/9SIQT8TOJO"], "isController": false}, {"data": [0.0, 500, 1500, "商品详情 GET /product/product_id"], "isController": false}, {"data": [0.45, 500, 1500, "商品详情 GET /product/LS4PSXUNUM"], "isController": false}, {"data": [0.5454545454545454, 500, 1500, "商品详情 GET /product/9SIQT8TOJO"], "isController": false}, {"data": [0.3181818181818182, 500, 1500, "5. 清空购物车 POST /cart/empty"], "isController": false}, {"data": [0.3, 500, 1500, "1. 浏览首页 GET /"], "isController": false}, {"data": [0.861904761904762, 500, 1500, "2. 添加商品 POST /cart"], "isController": false}, {"data": [0.6590909090909091, 500, 1500, "2. 查看商品详情 GET /product/2ZYFJ3GM2N"], "isController": false}, {"data": [0.5714285714285714, 500, 1500, "商品详情 GET /product/66VCHSJNUP"], "isController": false}, {"data": [0.5555555555555556, 500, 1500, "商品详情 GET /product/2ZYFJ3GM2N"], "isController": false}, {"data": [0.625, 500, 1500, "2. 查看商品详情 GET /product/66VCHSJNUP"], "isController": false}, {"data": [0.0, 500, 1500, "2. 查看商品详情 GET /product/product_id"], "isController": false}, {"data": [0.2733333333333333, 500, 1500, "4. 切换货币 POST /setCurrency"], "isController": false}, {"data": [0.5882352941176471, 500, 1500, "2. 查看商品详情 GET /product/OLJCESPC7Z"], "isController": false}, {"data": [0.575, 500, 1500, "商品详情 GET /product/6E92ZMYYFZ"], "isController": false}, {"data": [0.6475, 500, 1500, "4. 查看购物车 GET /cart"], "isController": false}, {"data": [0.7222222222222222, 500, 1500, "2. 查看商品详情 GET /product/1YMWWN1N4O"], "isController": false}, {"data": [0.6666666666666666, 500, 1500, "2. 查看商品详情 GET /product/LS4PSXUNUM"], "isController": false}, {"data": [1.0, 500, 1500, "4. 切换货币 POST /setCurrency-0"], "isController": false}, {"data": [0.34, 500, 1500, "4. 切换货币 POST /setCurrency-1"], "isController": false}, {"data": [0.62, 500, 1500, "3. 查看购物车 GET /cart"], "isController": false}, {"data": [0.6, 500, 1500, "商品详情 GET /product/L9ECAV7KIM"], "isController": false}, {"data": [0.5882352941176471, 500, 1500, "商品详情 GET /product/1YMWWN1N4O"], "isController": false}, {"data": [0.855, 500, 1500, "3. 加入购物车 POST /cart"], "isController": false}, {"data": [0.5952380952380952, 500, 1500, "2. 查看商品详情 GET /product/L9ECAV7KIM"], "isController": false}, {"data": [0.65, 500, 1500, "3. 提交订单 POST /cart/checkout"], "isController": false}, {"data": [0.6521739130434783, 500, 1500, "2. 查看商品详情 GET /product/0PUK6V6EV0"], "isController": false}, {"data": [0.5588235294117647, 500, 1500, "商品详情 GET /product/0PUK6V6EV0"], "isController": false}]}, function(index, item){
        switch(index){
            case 0:
                item = item.toFixed(3);
                break;
            case 1:
            case 2:
                item = formatDuration(item);
                break;
        }
        return item;
    }, [[0, 0]], 3);

    // Create statistics table
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 2815, 72, 2.5577264653641207, 974.4714031971606, 2, 2612, 999.0, 1897.0, 2095.2, 2398.0, 83.94966002624359, 687.8994551845999, 20.64099335150006], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["2. 查看商品详情 GET /product/6E92ZMYYFZ", 16, 0, 0.0, 675.3125, 208, 1126, 746.5, 967.8000000000002, 1126.0, 1126.0, 0.6202752471409189, 4.900492464624927, 0.1550688117852297], "isController": false}, {"data": ["5. 清空购物车 POST /cart/empty-1", 275, 0, 0.0, 1254.2909090909097, 69, 2299, 1298.0, 1800.0, 1902.2, 2202.0, 8.243899514359374, 85.94250606113977, 1.474738771434139], "isController": false}, {"data": ["商品详情 GET /product/OLJCESPC7Z", 15, 0, 0.0, 797.9333333333334, 97, 1296, 813.0, 1120.2, 1296.0, 1296.0, 0.9208103130755064, 7.386265538674033, 0.17445039134438306], "isController": false}, {"data": ["首页 GET /", 500, 0, 0.0, 1611.4900000000011, 115, 2612, 1602.5, 2099.0, 2309.95, 2495.99, 15.56178026766262, 163.3986928104575, 2.674680983504513], "isController": false}, {"data": ["5. 清空购物车 POST /cart/empty-0", 275, 0, 0.0, 158.04727272727288, 3, 1013, 101.0, 301.0, 495.4, 786.5200000000027, 8.26595328984941, 0.7345720208752894, 2.0518115588085006], "isController": false}, {"data": ["2. 查看商品详情 GET /product/9SIQT8TOJO", 23, 0, 0.0, 671.5217391304348, 295, 1201, 598.0, 1056.6000000000001, 1179.3999999999996, 1201.0, 0.7827122681640293, 6.225905808660881, 0.19567806704100732], "isController": false}, {"data": ["商品详情 GET /product/product_id", 13, 13, 100.0, 280.61538461538464, 13, 906, 209.0, 782.8, 906.0, 906.0, 0.9625351695542721, 4.940512549977788, 0.18235529579446172], "isController": false}, {"data": ["商品详情 GET /product/LS4PSXUNUM", 10, 0, 0.0, 918.1, 593, 1602, 848.5, 1561.7000000000003, 1602.0, 1602.0, 1.0418837257762035, 8.325098653365284, 0.19738812773494477], "isController": false}, {"data": ["商品详情 GET /product/9SIQT8TOJO", 11, 0, 0.0, 755.0, 207, 1003, 801.0, 1003.0, 1003.0, 1003.0, 0.7381064215258673, 5.91133863567738, 0.13983656814064283], "isController": false}, {"data": ["5. 清空购物车 POST /cart/empty", 275, 0, 0.0, 1412.534545454545, 76, 2500, 1400.0, 2096.4, 2203.0, 2496.48, 8.24216993855837, 86.6569337254608, 3.5203373201708374], "isController": false}, {"data": ["1. 浏览首页 GET /", 305, 0, 0.0, 1460.1836065573773, 145, 2577, 1417.0, 2015.6000000000001, 2206.5, 2508.7, 9.20699127599843, 96.67340839798351, 1.58245162556223], "isController": false}, {"data": ["2. 添加商品 POST /cart", 105, 9, 8.571428571428571, 275.5047619047618, 3, 1196, 201.0, 502.0, 801.8, 1184.1799999999996, 3.3285782215882076, 1.7244709938183547, 0.9719188361864003], "isController": false}, {"data": ["2. 查看商品详情 GET /product/2ZYFJ3GM2N", 22, 0, 0.0, 589.6363636363636, 194, 1079, 596.0, 869.9, 1051.9999999999995, 1079.0, 0.8240317626788524, 6.542068928384149, 0.2060079406697131], "isController": false}, {"data": ["商品详情 GET /product/66VCHSJNUP", 14, 0, 0.0, 820.7857142857144, 210, 1295, 849.5, 1152.5, 1295.0, 1295.0, 0.8339786739739083, 6.646698337999643, 0.15799986596771312], "isController": false}, {"data": ["商品详情 GET /product/2ZYFJ3GM2N", 18, 0, 0.0, 818.5, 120, 1602, 897.5, 1243.8000000000006, 1602.0, 1602.0, 1.0150566739976314, 8.12381268327412, 0.19230565894095752], "isController": false}, {"data": ["2. 查看商品详情 GET /product/66VCHSJNUP", 20, 0, 0.0, 690.1499999999999, 104, 1198, 699.5, 1166.6000000000006, 1197.9, 1198.0, 0.6097375080028048, 4.8215112534678815, 0.1524343770007012], "isController": false}, {"data": ["2. 查看商品详情 GET /product/product_id", 25, 25, 100.0, 165.96, 3, 887, 100.0, 435.4000000000002, 771.4999999999998, 887.0, 0.7649236606186702, 3.864956074258789, 0.19123091515466756], "isController": false}, {"data": ["4. 切换货币 POST /setCurrency", 75, 0, 0.0, 1476.4666666666665, 287, 2599, 1400.0, 2099.8, 2322.8, 2599.0, 2.3160300157490044, 24.667770319303337, 1.1037330543803847], "isController": false}, {"data": ["2. 查看商品详情 GET /product/OLJCESPC7Z", 17, 0, 0.0, 663.7647058823529, 101, 998, 700.0, 923.5999999999999, 998.0, 998.0, 0.6249540474965076, 4.968183635394456, 0.1562385118741269], "isController": false}, {"data": ["商品详情 GET /product/6E92ZMYYFZ", 20, 0, 0.0, 755.7999999999998, 50, 1312, 852.5, 1089.4, 1301.35, 1312.0, 1.1806375442739079, 9.398751106847698, 0.2236754722550177], "isController": false}, {"data": ["4. 查看购物车 GET /cart", 200, 0, 0.0, 647.5150000000003, 10, 1596, 601.5, 1071.5000000000005, 1103.9, 1298.99, 6.01015716560988, 90.57667810161674, 1.4203691739038975], "isController": false}, {"data": ["2. 查看商品详情 GET /product/1YMWWN1N4O", 18, 0, 0.0, 605.0555555555555, 195, 1199, 552.0, 1107.2, 1199.0, 1199.0, 0.845229151014275, 6.715976591848235, 0.21130728775356875], "isController": false}, {"data": ["2. 查看商品详情 GET /product/LS4PSXUNUM", 15, 0, 0.0, 559.8666666666667, 298, 900, 505.0, 838.8000000000001, 900.0, 900.0, 0.5103082261686058, 4.037548054024631, 0.12757705654215146], "isController": false}, {"data": ["4. 切换货币 POST /setCurrency-0", 75, 0, 0.0, 104.17333333333329, 2, 403, 98.0, 200.4, 222.60000000000025, 403.0, 2.352350782548694, 0.3170160234294138, 0.6684903102750682], "isController": false}, {"data": ["4. 切换货币 POST /setCurrency-1", 75, 0, 0.0, 1371.9466666666663, 200, 2395, 1396.0, 1942.8000000000006, 2199.6, 2395.0, 2.322269011642309, 24.421259114905872, 0.44676464384134257], "isController": false}, {"data": ["3. 查看购物车 GET /cart", 75, 0, 0.0, 700.8, 13, 1302, 794.0, 1000.4, 1098.0, 1302.0, 2.3581197924854584, 35.94747902255935, 0.5572900290834775], "isController": false}, {"data": ["商品详情 GET /product/L9ECAV7KIM", 15, 0, 0.0, 724.6000000000001, 289, 1098, 700.0, 1095.6, 1098.0, 1098.0, 0.9436336185203825, 7.537826438254907, 0.17877433788374433], "isController": false}, {"data": ["商品详情 GET /product/1YMWWN1N4O", 17, 0, 0.0, 749.2941176470586, 203, 1410, 702.0, 1320.3999999999999, 1410.0, 1410.0, 1.428451390639442, 11.460516054323167, 0.27062457986723804], "isController": false}, {"data": ["3. 加入购物车 POST /cart", 200, 25, 12.5, 187.16500000000008, 2, 799, 197.0, 300.0, 400.9, 799.0, 6.027727546714889, 4.297846264692586, 1.7600493520192888], "isController": false}, {"data": ["2. 查看商品详情 GET /product/L9ECAV7KIM", 21, 0, 0.0, 609.9047619047619, 195, 1127, 601.0, 1038.6000000000001, 1124.2, 1127.0, 0.8643753858818687, 6.836098284111957, 0.21609384647046717], "isController": false}, {"data": ["3. 提交订单 POST /cart/checkout", 30, 0, 0.0, 647.4666666666668, 102, 1497, 697.5, 903.5, 1272.0499999999997, 1497.0, 1.4778325123152711, 10.050415640394089, 0.7345866687192117], "isController": false}, {"data": ["2. 查看商品详情 GET /product/0PUK6V6EV0", 23, 0, 0.0, 604.4347826086955, 200, 1102, 599.0, 958.2000000000002, 1080.9999999999998, 1102.0, 0.9351494206139459, 7.401426547570645, 0.2337873551534865], "isController": false}, {"data": ["商品详情 GET /product/0PUK6V6EV0", 17, 0, 0.0, 788.0588235294118, 67, 1599, 885.0, 1281.3999999999996, 1599.0, 1599.0, 1.2774271115118725, 10.20973051923655, 0.24201255823564774], "isController": false}]}, function(index, item){
        switch(index){
            // Errors pct
            case 3:
                item = item.toFixed(2) + '%';
                break;
            // Mean
            case 4:
            // Mean
            case 7:
            // Median
            case 8:
            // Percentile 1
            case 9:
            // Percentile 2
            case 10:
            // Percentile 3
            case 11:
            // Throughput
            case 12:
            // Kbytes/s
            case 13:
            // Sent Kbytes/s
                item = item.toFixed(2);
                break;
        }
        return item;
    }, [[0, 0]], 0, summaryTableHeader);

    // Create error table
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["500/Internal Server Error", 72, 100.0, 2.5577264653641207], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 2815, 72, "500/Internal Server Error", 72, "", "", "", "", "", "", "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["商品详情 GET /product/product_id", 13, 13, "500/Internal Server Error", 13, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["2. 添加商品 POST /cart", 105, 9, "500/Internal Server Error", 9, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["2. 查看商品详情 GET /product/product_id", 25, 25, "500/Internal Server Error", 25, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["3. 加入购物车 POST /cart", 200, 25, "500/Internal Server Error", 25, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
