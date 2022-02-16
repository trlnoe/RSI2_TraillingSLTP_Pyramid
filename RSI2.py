
from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils

class RSI2_TrailingSL_TP_Pyramid(Strategy):
    def __init__(self):
        super().__init__()

        self.current_pyramiding_levels = 0
        self.last_opened_price = 0
        self.last_was_profitable = False
        self.risk_percent = 3

    #def before(self):
        self.vars["fast_sma_period"] = 50
        self.vars["slow_sma_period"] = 200
        self.vars["rsi_period"] = 2
        self.vars["rsi_ob_threshold"] = 90
        self.vars["rsi_os_threshold"] = 10

        self.vars["longTrailingPer"] = 0.03
        self.vars["shortTrailingPer"] = 0.03 
        self.vars["longStopPrice"] = 0
        self.vars["shortStopPrice"] = 0

        self.vars["longProfitPer"] = 0.03
        self.vars["shortProfitPer"] = 0.03 
        self.vars["longExitPrice"] = 0
        self.vars["shortExitPrice"] = 0

        self.vars["highestPricePeriod"] = 0
        self.vars["lowestPricePeriod"] = 0 
        self.vars["period"] = 20 

        self.vars["system_type"] = "S1" 
        self.vars["maximum_pyramiding_levels"] = 3

    @property
    def fast_sma(self):
        return ta.sma(self.candles, self.vars["fast_sma_period"])

    @property
    def slow_sma(self):
        return ta.sma(self.candles, self.vars["slow_sma_period"])
    
    @property
    def atr(self):
        return ta.atr(self.candles)

    @property
    def rsi(self):
        return ta.rsi(self.candles, self.vars["rsi_period"])

    @property 
    def up_trend(self): 
        if(self.index % self.vars["period"] == 0): 
            self.vars["highestPricePeriod"] = self.current_candle[2]
        else: 
            if(self.vars["highestPricePeriod"] < self.current_candle[2]): 
                self.vars["highestPricePeriod"] = self.current_candle[2]
        return self.vars["highestPricePeriod"]
    
    @property
    def down_trend(self): 
        if(self.index % self.vars["period"] == 0): 
            self.vars["lowestPricePeriod"] = self.current_candle[2]
        else: 
            if(self.vars["lowestPricePeriod"] > self.current_candle[2]): 
                self.vars["lowestPricePeriod"] = self.current_candle[2]
        return self.vars["lowestPricePeriod"]

    def should_long(self) -> bool:
        # Enter long if current price is above sma(200) and RSI(2) is below oversold threshold
        return self.price > self.slow_sma and self.rsi <= self.vars["rsi_os_threshold"]

    def should_short(self) -> bool:
        # Enter long if current price is below sma(200) and RSI(2) is above oversold threshold
        return self.price < self.slow_sma and self.rsi >= self.vars["rsi_ob_threshold"]

    def should_cancel(self) -> bool:
        return False

    def go_long(self):
        # Open long position and use entire balance to buy 
        # sample with pyramiding = 3      

        stopValue = self.price * (1 - self.vars["longTrailingPer"])       
        entry = self.price
        self.vars["longStopPrice"] = max(stopValue, self.vars["longStopPrice"])
        self.vars["longExitPrice"] = self.atr * (1 + self.vars["longProfitPer"])

        
        qty = utils.risk_to_qty(self.capital, self.risk_percent , entry, self.vars["longStopPrice"], fee_rate=self.fee_rate)        
        
        #pyramiding = 3 
        self.buy = qty, entry

        #trailing stoploss & take profit 
        self.stop_loss = qty, self.vars["longStopPrice"]
        self.take_profit = qty, self.vars["longExitPrice"]
        self.vars["shortStopPrice"] = 999999.9

    def go_short(self):
        # Open short position and use entire balance to sell
        # sample with pyramiding = 3 

        stopValue = self.price * (1 + self.vars["shortTrailingPer"])
        entry = self.price
        self.vars["shortStopPrice"] = min(stopValue, self.vars["shortStopPrice"])
        self.vars["shortExitPrice"] = self.atr * (1 - self.vars["shortProfitPer"])

        
        qty = utils.risk_to_qty(self.capital, self.risk_percent, entry, self.vars["shortStopPrice"], fee_rate=self.fee_rate)         
        self.sell = qty, entry

        #trailing stoploss & take profit 
        self.stop_loss = qty, self.vars["shortStopPrice"]
        self.take_profit = qty, self.vars["shortExitPrice"]
        self.vars["longStopPrice"] = 0
    
    def update_position(self):
        # Handle for pyramiding rules
        if self.current_pyramiding_levels < self.vars["maximum_pyramiding_levels"]:
            # if self.is_long and self.price > self.last_opened_price + (self.vars["pyramiding_threshold"] * self.atr):
            if self.is_long and self.price > self.up_trend:
                qty = utils.risk_to_qty(self.capital, self.risk_percent, self.price, self.fee_rate)
                self.buy = qty, self.price
            
            if self.is_short and self.price < self.down_trend:
                qty = utils.risk_to_qty(self.capital, self.risk_percent, self.price, self.fee_rate)
                self.sell = qty, self.price 
        
        if (self.is_long and self.price > self.fast_sma) or (self.is_short and self.price < self.fast_sma):
            self.liquidate()
            self.current_pyramiding_levels = 0
    
    # timestamp: UTC times 
    # action long / short / sell/ buy/ liquidate / DCA 
    # pyramid 
    # param 
    # entry price, stoploss, takeprofit 
    # thua, thằng, lời lỗ sau lệnh đó 

    def on_increased_position(self, order):        
        self.current_pyramiding_levels += 1
        self.last_opened_price = self.price
       
    def on_stop_loss(self, order):
        # Reset tracked pyramiding levels
        self.current_pyramiding_levels = 0 

    def on_take_profit(self, order):
        self.last_was_profitable = True

        # Reset tracked pyramiding levels
        self.current_pyramiding_levels = 0

    def hyperparameters(self):
        return [
                {'name':'stop_loss', 'type': float, 'min': 0.5, 'max': 0.99, 'default': 0.9},
                {'name':'take_profit', 'type': float, 'min': 1.0, 'max': 1.2, 'default': 1.1},
        ]
     
