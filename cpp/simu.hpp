/*
 * simu.hpp
 *
 *  Created on: 12 Feb 2021
 *      Author: joubertd
 */
#include <vector>
#include <random>
#include <iostream>
#include <algorithm>
#include <memory>
#include <limits>
#include <cstring>

#ifndef SIMU_HPP_
#define SIMU_HPP_

using vdouble = std::vector<double>;
using vtime = std::vector<uint64_t>;

class Event{
public:
    uint16_t x_;
    uint16_t y_;
    uint8_t p_;
    uint64_t ts_;
    Event(uint16_t x, uint16_t y, uint8_t p, uint64_t ts){
        x_=x;y_=y;p_=p;ts_=ts;
    }
};

class SimuICNS{
public:
	// Shape
	int x_;
	int y_;
    // States
    double time_;
	vdouble last_v_;
    vdouble cur_v_;
    vtime time_px_;
    vtime cur_ref_;
	// Thresholds
	double m_th_pos_;
	double m_th_neg_;
	double m_th_noise_;
	vdouble cur_th_pos_;
	vdouble cur_th_neg_;
	std::default_random_engine generator_cur_th_pos_;
    std::normal_distribution<double> distribution_cur_th_pos_;
	std::default_random_engine generator_cur_th_neg_;
    std::normal_distribution<double> distribution_cur_th_neg_;

    // Latency
    double tau_;
    double m_jit_;
    double m_lat_;
    double ref_;
    vdouble tau_p_;
    std::default_random_engine generator_lat_;
    std::normal_distribution<double> distribution_lat_;

    // Noise
    double m_bgn_pos_;
    double m_bgn_neg_;
    uint64_t m_bgn_pos_per = 1e6 / m_bgn_pos_;
    uint64_t m_bgn_neg_per = 1e6 / m_bgn_neg_;
    uint8_t noise_model_ = 1;
    vtime bgn_neg_next_;
    vtime bgn_pos_next_;
    vdouble bgn_hist_pos_;
    vdouble bgn_hist_neg_;
    std::default_random_engine generator_noise_;
    std::uniform_real_distribution<double> distribution_noise_;

    // Utils
    vtime PER;
    bool debug_;

    SimuICNS(const int & x, const int & y){
        set_shape(x, y);
        debug_ = false;
        PER.resize(72);
        for(int i=-3; i < 5; i++){
            for(int j=1; j < 10; j++){
                PER[(i+3) * 9 + j - 1] = 1e6/(j * (std::pow(10.0, i)));
            }
        }
    }

    ~SimuICNS(){
    }

	void set_th(const double& th_pos, const double& th_neg, const double& th_noise){
		m_th_pos_ = th_pos;
		m_th_neg_ = th_neg;
		m_th_noise_ = th_noise;
        distribution_cur_th_pos_ = std::normal_distribution<double>(m_th_pos_, m_th_noise_);
        distribution_cur_th_neg_ = std::normal_distribution<double>(-m_th_neg_, m_th_noise_);
		for(int i = 0; i < x_ * y_; i++){
		    cur_th_pos_.at(i) = std::max(distribution_cur_th_pos_(generator_cur_th_pos_), 0.0);
		    cur_th_neg_.at(i) = std::min(0.0, distribution_cur_th_neg_(generator_cur_th_neg_));
		}

	}

	void set_lat(const double& lat, const double& jit, const double& ref, const double& tau){
	    m_lat_ = lat;
	    m_jit_ = jit;
	    ref_ = ref;
	    tau_ = tau;
	}

	void set_shape(const int & x, const int & y){
		x_ = x;
		y_ = y;
        cur_th_pos_.resize(x_ * y_);
		cur_th_neg_.resize(x_ * y_);
		bgn_neg_next_.resize(x_ * y_);
		bgn_pos_next_.resize(x_ * y_);
		tau_p_.resize(x_ * y_);
		last_v_.resize(x_ * y_);
		cur_v_.resize(x_ * y_);
		cur_ref_.resize(x_ * y_);
		time_px_.resize(x_ * y_);
		bgn_hist_neg_.resize(x_ * y_ * 72);
		bgn_hist_pos_.resize(x_ * y_ * 72);
	}

	    void init_next_noise(int&& x, int&& y, int&& p){
        double prob = distribution_noise_(generator_noise_);
        int position = 0;
        int id = x * y_ + y;
        if(p){
            while(position < 72){
                if(bgn_hist_pos_.at(id * 72 + position) >= prob){
                    bgn_pos_next_.at(id) = (PER[position] * distribution_noise_(generator_noise_));
                    position = 72;
                }
                position ++;
            }
        }else{
            while(position < 72){
                if(bgn_hist_neg_.at(id * 72 + position) > prob){
                    bgn_neg_next_.at(id) = (PER[position] * distribution_noise_(generator_noise_));
                    position = 72;
                }
                position++;
            }
        }
    }

    void update_next_noise(int&& x, int&& y, int&& p){
        double prob = distribution_noise_(generator_noise_);
        int position = 0;
        int id = x * y_ + y;
        if(p){
            while(position < 72){
                if(bgn_hist_pos_.at(id * 72 + position) >= prob){
                    bgn_pos_next_.at(id) += PER[position];
                    position = 72;
                }
                position ++;
            }
        }else{
            while(position < 72){
                if(bgn_hist_neg_.at(id * 72 + position) > prob){
                    bgn_neg_next_.at(id) += PER[position];
                    position = 72;
                }
                position++;
            }
        }
    }

	void init_noise(const double * distrib_pos, const double * distrib_neg, long int& size){
	    std::default_random_engine generator_init_noise;
        std::uniform_int_distribution<int> distribution_index(0, size - 1);
        distribution_noise_ = std::uniform_real_distribution<double>(0.0, 1.0);
        int index;
        for(int i = 0; i < x_ * y_; i++){
            index = distribution_index(generator_init_noise);
            for(int j = 0; j < 72; j++){
                bgn_hist_pos_.at(i * 72 + j) = distrib_pos[index * 72 + j];
                bgn_hist_neg_.at(i * 72 + j) = distrib_neg[index * 72 + j];
                init_next_noise(i / y_, i % y_, 0);
                init_next_noise(i / y_, i % y_, 1);
            }
        }
	}

	void disableNoise(){
        for(int i = 0; i < x_ * y_; i++){
            bgn_neg_next_.at(i) = -1;
            bgn_pos_next_.at(i) = -1;
            std::cout << bgn_pos_next_.at(i) << std::endl;
        }
	}

	void init_img(const double * img){
	    time_ = 0;
	    for(int i=0; i < x_ * y_; i++){
	        if(img[i] > 0){
	            last_v_[i] = std::log(img[i]);
	            cur_v_[i] = std::log(img[i]);
	            tau_p_[i] = tau_ * 255 / img[i];
	            cur_ref_[i] = -1;
	            time_px_[i] = 0;
	        }
	    }
	}

    /// TO CHECK: The noise version in Python does not manage the exponential reponse...
	void check_noise(const uint64_t & dt, std::vector<Event>& ev_pk){
	    uint64_t next_t = time_ + dt;
	    auto nb_ev_before = ev_pk.size();
	    for(int i=0; i < x_ * y_; i++){
            if(bgn_pos_next_.at(i) < next_t){
                ev_pk.push_back(Event(i / y_, i % y_, 1, bgn_pos_next_[i]));
                cur_ref_[i] = bgn_pos_next_[i];
                update_next_noise(i / y_, i % y_, 1);
            }
            if(bgn_neg_next_.at(i) < next_t){
                ev_pk.push_back(Event(i / y_, i % y_, 0, bgn_neg_next_[i]));
                cur_ref_[i] = bgn_neg_next_[i];
                update_next_noise(i / y_, i % y_, 0);
            }
	    }
	    auto nb_ev_after = ev_pk.size();
	    if(debug_){ std::cout << nb_ev_after - nb_ev_before << " Noise Events Created " << std::endl;}
	}

	void update_img(const double * img, const uint64_t& dt, std::vector<Event>& ev_pk){
	    double img_l, target, amp;
	    uint64_t t_event;
	    check_noise(dt, ev_pk);
        auto nb_ev_before = ev_pk.size();
	    for(int i = 0; i < x_ * y_; i++){
	        if(img[i] > 0){
	            img_l = std::log(img[i]);
                tau_p_[i] = tau_ * std::log(255) / img_l;
                // Update ref
                if (cur_ref_[i] < time_ + dt){
                    last_v_[i] = cur_v_[i] + (img_l - cur_v_[i]) * (1 - std::exp(-((double)(cur_ref_[i] - time_px_[i])) / tau_p_[i]));
                    cur_v_[i] = last_v_[i];
                    time_px_[i] = cur_ref_[i];
                    cur_ref_[i] = std::numeric_limits<uint64_t>::max();
                }
                target = cur_v_[i] + (img_l - cur_v_[i]) * (1 - std::exp(-((double)(time_ + dt - time_px_[i])) / tau_p_[i]));
                // Check contrast
                while((target - last_v_[i] > cur_th_pos_[i])&(cur_ref_[i] == std::numeric_limits<uint64_t>::max())){
                    amp = (last_v_[i] + cur_th_pos_[i] - cur_v_[i]) / (img_l - cur_v_[i]);
                    distribution_lat_ = std::normal_distribution<double>(m_lat_ - tau_p_[i] * std::log(1-amp), std::sqrt(std::pow(m_jit_, 2) + std::pow( m_th_noise_ * tau_p_[i] / (img_l- cur_v_[i]),2)));
                    t_event = std::clamp(distribution_lat_(generator_lat_), (double)0, (double)1e4);
                    ev_pk.push_back(Event(i / y_, i % y_, 1, time_px_[i] + t_event));
                    cur_ref_[i] = time_px_[i] + t_event + ref_;
                    cur_th_pos_[i] = std::max(0.0, (double)distribution_cur_th_pos_(generator_cur_th_pos_));
                    if (cur_ref_[i] < time_ + dt){
                        last_v_[i] = cur_v_[i] + (img_l - cur_v_[i]) * (1 - std::exp(-((double)(cur_ref_[i] - time_px_[i])) / tau_p_[i]));
                        cur_v_[i] = last_v_[i];
                        time_px_[i] = cur_ref_[i];
                        cur_ref_[i] = std::numeric_limits<uint64_t>::max();
                    }
                }
                while((target - last_v_[i] < cur_th_neg_[i])&(cur_ref_[i] == std::numeric_limits<uint64_t>::max())){
                    amp = (last_v_[i] + cur_th_neg_[i] - cur_v_[i]) / (img_l - cur_v_[i]);
                    distribution_lat_ = std::normal_distribution<double>(m_lat_ - tau_p_[i] * std::log(1-amp), std::sqrt(std::pow(m_jit_, 2) + std::pow( m_th_noise_ * tau_p_[i] / (img_l- cur_v_[i]),2)));
                    t_event = std::clamp(distribution_lat_(generator_lat_), (double)0, (double)1e4);
                    ev_pk.push_back(Event(i / y_, i % y_, 0, time_px_[i] + t_event));
                    cur_ref_[i] = time_px_[i] + t_event + ref_;
                    cur_th_neg_[i] = std::min(0.0,(double) distribution_cur_th_neg_(generator_cur_th_neg_));
                    if (cur_ref_[i] < time_ + dt){
                        last_v_[i] = cur_v_[i] + (img_l - cur_v_[i]) * (1 - std::exp(-((double)(cur_ref_[i] - time_px_[i])) / tau_p_[i]));
                        cur_v_[i] = last_v_[i];
                        time_px_[i] = cur_ref_[i];
                        cur_ref_[i] = std::numeric_limits<uint64_t>::max();
                    }
                }
                cur_v_[i] = cur_v_[i] + (img_l - cur_v_[i]) * (1 - std::exp(-((double)(time_ + dt - time_px_[i])) / tau_p_[i]));
                time_px_[i] = time_ + dt;
            }
	    }
        auto nb_ev_after = ev_pk.size();
	    if(debug_){ std::cout << nb_ev_after - nb_ev_before << " Signal Events Created " << std::endl;}
	    time_ += dt;
	}

    void print(){
        std::cout<< x_ << y_ <<std::endl;
    }
};


#endif /* SIMU_HPP_ */
